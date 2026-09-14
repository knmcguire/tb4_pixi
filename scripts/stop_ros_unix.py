"""Stop this workspace's ROS/Gazebo processes, including orphaned nodes."""

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import re
import signal
import subprocess
import time


@dataclass(frozen=True)
class Process:
    pid: int
    parent: int
    started: str
    command: str


def processes():
    result = subprocess.run(
        ["ps", "-ww", "-u", str(os.getuid()), "-o", "pid=,ppid=,stat=,lstart=,args="],
        check=True, capture_output=True, text=True,
    )
    found = {}
    for line in result.stdout.splitlines():
        fields = line.split(None, 8)
        if len(fields) == 9 and not fields[2].startswith("Z"):
            pid, parent = map(int, fields[:2])
            found[pid] = Process(pid, parent, " ".join(fields[3:8]), fields[8])
    return found


def simulator_patterns(root, prefix):
    # Match executable paths, not arbitrary mentions of the workspace in arguments.
    packages = (
        "robot_state_publisher", "joint_state_publisher", "tf2_ros",
        "ros_gz_sim", "ros_gz_bridge", "controller_manager",
        "irobot_create_nodes", "irobot_create_toolbox", "irobot_create_gz_toolbox",
        "turtlebot4_node",
        "turtlebot4_gz_toolbox", "teleop_twist_keyboard",
    )
    python = rf"(?:{re.escape(str(prefix))}/bin/python[\d.]*(?:\s+))?"
    paths = "|".join(re.escape(str(path)) for path in (prefix, root / "install"))
    nodes = rf"{python}(?:{paths})/lib/(?:{'|'.join(packages)})/[^\s]+(?:\s|$)"
    launch = (
        rf"{python}{re.escape(str(prefix))}/bin/ros2\s+launch\s+"
        rf"(?:sim\.launch\.xml|{re.escape(str(root / 'sim.launch.xml'))}"
        r"|turtlebot4_gz_bringup|irobot_create_gz_bringup)(?:\s|$)"
    )
    # Gazebo changes its process title to 'gz sim ...', retaining resource paths.
    gazebo = rf"(?:{re.escape(str(prefix))}/bin/)?gz\s+sim\s+"
    # Daemons are DDS participants too; a stuck one can outlive every simulator node.
    daemon = (
        rf"{re.escape(str(prefix))}/bin/python[\d.]*\s+-c\s+"
        r"from ros2cli\.daemon\.daemonize import main; main\(\)\s+"
        r"--name ros2-daemon(?:\s|$)"
    )
    return re.compile(nodes), re.compile(launch), re.compile(gazebo), re.compile(daemon)


def targets(snapshot, root, prefix):
    protected = set()
    pid = os.getpid()
    while pid in snapshot and pid not in protected:
        protected.add(pid)
        pid = snapshot[pid].parent

    nodes, launch, gazebo, daemon = simulator_patterns(root, prefix)
    resource_path = str(prefix / "share") + "/"
    selected = {
        pid: proc for pid, proc in snapshot.items()
        if pid not in protected and (
            nodes.match(proc.command)
            or launch.match(proc.command)
            or daemon.match(proc.command)
            or (gazebo.match(proc.command) and resource_path in proc.command)
        )
    }
    # Include children even if their command line no longer contains a workspace path.
    while True:
        children = {
            pid: proc for pid, proc in snapshot.items()
            if pid not in protected and pid not in selected and proc.parent in selected
        }
        if not children:
            return selected
        selected.update(children)


def survivors(selected):
    current = processes()
    # Do not signal a PID that has been reused since discovery.
    return {
        pid: proc for pid, proc in selected.items()
        if pid in current and current[pid].started == proc.started
    }


def send(selected, sig):
    for pid, proc in survivors(selected).items():
        try:
            os.kill(pid, sig)
            print(f"[stop] {sig.name} PID {pid}: {proc.command}", flush=True)
        except ProcessLookupError:
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="list targets without stopping them")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    prefix = Path(os.environ["CONDA_PREFIX"])
    if not prefix.is_relative_to(root / ".pixi" / "envs"):
        parser.error("CONDA_PREFIX must be a Pixi environment inside this workspace")

    selected = targets(processes(), root, prefix)
    if not selected:
        print("[stop] no matching ROS/Gazebo processes found")
        return
    if args.dry_run:
        for pid, proc in selected.items():
            print(f"[stop] would stop PID {pid}: {proc.command}")
        return

    send(selected, signal.SIGINT)
    deadline = time.monotonic() + 5
    while selected and time.monotonic() < deadline:
        time.sleep(0.2)
        selected = survivors(selected)
    if selected:
        send(selected, signal.SIGKILL)


if __name__ == "__main__":
    main()
