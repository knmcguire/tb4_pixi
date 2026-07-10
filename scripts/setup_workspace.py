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

Idempotent: re-running skips repos that are already cloned.
"""

import subprocess
import sys
from pathlib import Path

ROS_DISTRO = "jazzy"

REPOS = {
    # the simulator itself (what the Dockerfile clones)
    "turtlebot4_simulator": "https://github.com/turtlebot/turtlebot4_simulator",
    # its source-only dependencies (rosdep debs in the container)
    "turtlebot4": "https://github.com/turtlebot/turtlebot4",
    "turtlebot4_desktop": "https://github.com/turtlebot/turtlebot4_desktop",
    "create3_sim": "https://github.com/iRobotEducation/create3_sim",
    "irobot_create_msgs": "https://github.com/iRobotEducation/irobot_create_msgs",
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
    for name, url in REPOS.items():
        dest = src / name
        if dest.exists():
            print(f"[setup] {name}: already present, skipping")
            continue
        print(f"[setup] cloning {url} (branch: {ROS_DISTRO}) ...")
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "-b", ROS_DISTRO, url, str(dest)]
        )
        if result.returncode != 0:
            failures.append(name)

    if failures:
        print(f"[setup] FAILED to clone: {', '.join(failures)}", file=sys.stderr)
        return 1

    patch_turtlebot4_node_for_windows(src)

    print("[setup] done. Next: pixi run build")
    return 0


if __name__ == "__main__":
    sys.exit(main())