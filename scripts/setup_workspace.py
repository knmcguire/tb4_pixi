#!/usr/bin/env python3
"""Clone the TurtleBot 4 simulation sources into ./src.

This replaces the Dockerfile's:

    RUN git clone https://github.com/turtlebot/turtlebot4_simulator -b ${ROS_DISTRO}
    RUN rosdep install -y --from-paths src --ignore-src

Inside the container, rosdep pulls the TurtleBot 4 / iRobot Create 3 packages
as prebuilt debs. Those debs don't exist as conda packages on RoboStack, so we
build them from source alongside the simulator. Everything else (nav2, slam
toolbox, ros_gz, etc.) comes as binaries from the robostack-jazzy channel and
is declared in pixi.toml.

We also build ros2_control's controller_manager from source with a one-line
patch that disables the pal_statistics introspection publisher thread. On
Windows that thread segfaults the Gazebo server the instant a robot is spawned
(controller_manager -> pal_statistics::startPublishThread -> joinPublisherThread),
and the crash is NOT fixed by guarding the registry (pal_statistics#26 was
tested and ruled out). Since the publisher thread is started unconditionally in
the controller_manager constructor with no runtime toggle, the only no-config
fix is to not start it. See knmcguire/tb4_pixi#4 and RoboStack/ros-jazzy#256.

Idempotent: re-running skips repos that are already cloned.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROS_DISTRO = "jazzy"

# name -> (url, branch)
REPOS = {
    # the simulator itself (what the Dockerfile clones)
    "turtlebot4_simulator": (
        "https://github.com/turtlebot/turtlebot4_simulator", ROS_DISTRO),
    # its source-only dependencies (rosdep debs in the container)
    "turtlebot4": (
        "https://github.com/turtlebot/turtlebot4", ROS_DISTRO),
    "turtlebot4_desktop": (
        "https://github.com/turtlebot/turtlebot4_desktop", ROS_DISTRO),
    "create3_sim": (
        "https://github.com/iRobotEducation/create3_sim", ROS_DISTRO),
    "irobot_create_msgs": (
        "https://github.com/iRobotEducation/irobot_create_msgs", ROS_DISTRO),
    # ros2_control: built from source ONLY so we can patch controller_manager
    # to not start the pal_statistics publisher thread (Windows spawn segfault).
    # controller_manager lives in this repo.
    "ros2_control": (
        "https://github.com/ros-controls/ros2_control", ROS_DISTRO),
}


def patch_turtlebot4_node_for_windows(src: Path) -> None:
    """Guard POSIX-only network code in turtlebot4_node with #ifndef _WIN32.

    turtlebot4.cpp uses <ifaddrs.h> to read the robot's Wi-Fi IP for the HMI
    display. That header doesn't exist on Windows, and in simulation the IP
    readout is cosmetic anyway, so on Windows we fall back to UNKNOWN_IP.
    The #ifdef guards make this a no-op on Linux/macOS, so we always apply it.
    Idempotent: skipped if the guards are already present.
    """
    cpp = src / "turtlebot4" / "turtlebot4_node" / "src" / "turtlebot4.cpp"
    if not cpp.exists():
        print(f"[setup] {cpp} not found, skipping Windows patch")
        return
    text = cpp.read_text()
    if "_WIN32" in text:
        print("[setup] turtlebot4_node: Windows patch already applied")
        return

    old_includes = (
        "#include <stdio.h>\n"
        "#include <sys/types.h>\n"
        "#include <ifaddrs.h>\n"
        "#include <netinet/in.h>\n"
        "#include <string.h>\n"
        "#include <arpa/inet.h>\n"
    )
    new_includes = (
        "#include <stdio.h>\n"
        "#include <string.h>\n"
        "#ifndef _WIN32\n"
        "#include <sys/types.h>\n"
        "#include <ifaddrs.h>\n"
        "#include <netinet/in.h>\n"
        "#include <arpa/inet.h>\n"
        "#endif\n"
    )
    old_body = (
        "std::string Turtlebot4::get_ip()\n"
        "{\n"
        "  struct ifaddrs * ifAddrStruct = NULL;\n"
    )
    new_body = (
        "std::string Turtlebot4::get_ip()\n"
        "{\n"
        "#ifdef _WIN32\n"
        "  // <ifaddrs.h> is POSIX-only; the IP readout is cosmetic in simulation.\n"
        "  return std::string(UNKNOWN_IP);\n"
        "#else\n"
        "  struct ifaddrs * ifAddrStruct = NULL;\n"
    )
    old_tail = "  return std::string(UNKNOWN_IP);\n}\n"
    new_tail = "  return std::string(UNKNOWN_IP);\n#endif\n}\n"

    if old_includes not in text or old_body not in text or old_tail not in text:
        print(
            "[setup] WARNING: turtlebot4.cpp changed upstream; "
            "Windows patch not applied (build may fail on Windows)"
        )
        return

    text = text.replace(old_includes, new_includes)
    text = text.replace(old_body, new_body)
    text = text.replace(old_tail, new_tail)
    cpp.write_text(text)
    print("[setup] turtlebot4_node: applied Windows compatibility patch")


def prune_ros2_control_test_packages(src: Path) -> None:
    """Remove ros2_control packages we neither build nor need.

    We only cloned ros2_control to patch controller_manager. The repo also
    contains test-only packages (ros2_control_test_assets, hardware_interface_
    testing). When colcon does a --packages-select controller_manager build, it
    still tries to resolve controller_manager's *test* dependency on
    hardware_interface_testing through the merge-install overlay and fails,
    because that package is a conda binary, not something we built. Deleting the
    test packages from src/ keeps colcon from discovering them at all, so the
    dependency graph no longer references them. Idempotent: missing dirs are a
    no-op.
    """
    ros2_control = src / "ros2_control"
    if not ros2_control.exists():
        return
    test_pkgs = ["ros2_control_test_assets", "hardware_interface_testing"]
    for pkg in test_pkgs:
        pkg_dir = ros2_control / pkg
        if pkg_dir.exists():
            shutil.rmtree(pkg_dir)
            print(f"[setup] ros2_control: removed test-only package '{pkg}'")


def patch_controller_manager_publisher_thread(src: Path) -> None:
    """Disable the pal_statistics introspection publisher thread.

    controller_manager.cpp starts the publisher thread unconditionally in the
    constructor:

        START_ROS2_CONTROL_INTROSPECTION_PUBLISHER_THREAD(...);

    On Windows this thread crashes the Gazebo server the instant a robot with a
    gz_ros2_control plugin is spawned. There is no parameter to disable it, so
    we comment out every invocation of that macro. Introspection data on the
    ~/introspection_data topics is a diagnostics feature (PlotJuggler etc.) and
    is not needed to drive the robot, so losing it is harmless for the workshop.

    Robust to surrounding-line changes: matches the macro call by regex rather
    than an exact multi-line block. Idempotent: skipped if already commented.
    """
    cpp = (
        src / "ros2_control" / "controller_manager" / "src"
        / "controller_manager.cpp"
    )
    if not cpp.exists():
        print(f"[setup] {cpp} not found, skipping publisher-thread patch")
        return

    text = cpp.read_text()
    marker = "// [tb4_pixi patch] publisher thread disabled (Windows segfault)"
    if marker in text:
        print("[setup] controller_manager: publisher-thread patch already applied")
        return

    # Match a whole line that invokes the start-publisher-thread macro (its
    # argument list is on the same line, terminated by ');'). We comment it out.
    pattern = re.compile(
        r"^([ \t]*)(START_ROS2_CONTROL_INTROSPECTION_PUBLISHER_THREAD\s*\([^;]*\);)",
        re.MULTILINE,
    )

    matches = list(pattern.finditer(text))
    if not matches:
        print(
            "[setup] WARNING: no START_ROS2_CONTROL_INTROSPECTION_PUBLISHER_THREAD "
            "call found in controller_manager.cpp; upstream may have changed. "
            "Publisher-thread patch NOT applied (Windows will still segfault)."
        )
        return

    def _comment(m: "re.Match") -> str:
        indent, call = m.group(1), m.group(2)
        return f"{indent}{marker}\n{indent}// {call}"

    new_text = pattern.sub(_comment, text)
    cpp.write_text(new_text)
    print(
        f"[setup] controller_manager: commented out {len(matches)} publisher-thread "
        "start call(s) to prevent the Windows spawn segfault"
    )


def patch_gz_launch_for_windows(src: Path) -> None:
    """Fix two Windows problems in the Gazebo bringup launch files.

    1. GZ_SIM_RESOURCE_PATH / GZ_GUI_PLUGIN_PATH are joined with ':', but on
       Windows the list separator is ';' and drive letters contain ':', so
       the paths get mangled and Gazebo can't find any models. -> os.pathsep.
    2. The combined `gz sim` command forks server + GUI, which Windows cannot
       do, so the process exits immediately. -> run the server headless (-s)
       and start the GUI as a separate process, Windows only.

    All changes are no-ops on Linux/macOS (os.pathsep == ':', os.name guard).
    Idempotent: files already containing os.pathsep are skipped.
    """
    tb4_launch = (
        src / "turtlebot4_simulator" / "turtlebot4_gz_bringup" / "launch" / "sim.launch.py"
    )
    create3_launch = (
        src / "create3_sim" / "irobot_create_gz" / "irobot_create_gz_bringup"
        / "launch" / "sim.launch.py"
    )

    for lf in (tb4_launch, create3_launch):
        if not lf.exists():
            print(f"[setup] {lf} not found, skipping launch patch")
            continue
        text = lf.read_text()
        if "os.pathsep" in text:
            print(f"[setup] {lf.name} ({lf.parent.parent.name}): already patched")
            continue

        n = text.count("':'.join([")
        text = text.replace("':'.join([", "os.pathsep.join([")
        print(f"[setup] {lf}: fixed {n} path join(s) for Windows")

        if lf == tb4_launch:
            old_imports = (
                "from launch.actions import IncludeLaunchDescription, "
                "SetEnvironmentVariable"
            )
            new_imports = (
                "from launch.actions import ExecuteProcess, "
                "IncludeLaunchDescription, SetEnvironmentVariable"
            )
            old_args = (
                "            ('gz_args', [\n"
                "                LaunchConfiguration('world'),\n"
                "                '.sdf',\n"
                "                ' -r',\n"
            )
            new_args = (
                "            ('gz_args', [\n"
                "                LaunchConfiguration('world'),\n"
                "                '.sdf',\n"
                "                # Windows can't fork server+GUI from one\n"
                "                # `gz sim` call; run the server headless here\n"
                "                # and launch the GUI separately below.\n"
                "                ' -s' if os.name == 'nt' else '',\n"
                "                ' -r',\n"
            )
            old_ld = (
                "    ld.add_action(gazebo)\n"
                "    ld.add_action(clock_bridge)\n"
            )
            new_ld = (
                "    ld.add_action(gazebo)\n"
                "    if os.name == 'nt':\n"
                "        # Companion GUI process for the headless server above.\n"
                "        ld.add_action(ExecuteProcess(\n"
                "            cmd=['gz', 'sim', '-g', '-v', '4', '--gui-config',\n"
                "                 PathJoinSubstitution([\n"
                "                     pkg_turtlebot4_gz_bringup,\n"
                "                     'gui',\n"
                "                     LaunchConfiguration('model'),\n"
                "                     'gui.config'\n"
                "                 ])],\n"
                "            shell=True,\n"
                "            output='screen',\n"
                "        ))\n"
                "    ld.add_action(clock_bridge)\n"
            )
            if old_imports in text and old_args in text and old_ld in text:
                text = text.replace(old_imports, new_imports)
                text = text.replace(old_args, new_args)
                text = text.replace(old_ld, new_ld)
                print(f"[setup] {lf}: split Gazebo server/GUI for Windows")
            else:
                print(
                    "[setup] WARNING: sim.launch.py changed upstream; "
                    "server/GUI split not applied (Gazebo may not start on Windows)"
                )
        lf.write_text(text)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    src = root / "src"
    src.mkdir(exist_ok=True)

    # Keep a place for your own workshop code, like the container's
    # /opt/ros/overlay_ws/src/workshop volume mount -- except here it's just
    # a normal folder on your machine, so no chown gymnastics afterwards.
    workshop = src / "workshop"
    workshop.mkdir(exist_ok=True)
    keep = workshop / ".gitkeep"
    keep.touch(exist_ok=True)

    failures = []
    for name, (url, branch) in REPOS.items():
        dest = src / name
        if dest.exists():
            print(f"[setup] {name}: already present, skipping")
            continue
        print(f"[setup] cloning {url} (branch: {branch}) ...")
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "-b", branch, url, str(dest)]
        )
        if result.returncode != 0:
            failures.append(name)

    if failures:
        print(f"[setup] FAILED to clone: {', '.join(failures)}", file=sys.stderr)
        return 1

    patch_turtlebot4_node_for_windows(src)
    prune_ros2_control_test_packages(src)
    patch_controller_manager_publisher_thread(src)
    patch_gz_launch_for_windows(src)

    print("[setup] done. Next: pixi run build")
    return 0


if __name__ == "__main__":
    sys.exit(main())