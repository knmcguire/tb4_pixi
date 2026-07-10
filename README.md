# ROSCon 2025 Intro to ROS Workshop — pixi edition

A cross-platform (Linux, macOS, Windows) replacement for the
[turtlebot4_docker](https://github.com/kscottz/turtlebot4_docker) container.
Instead of Docker + rocker + X11 forwarding, everything — ROS 2 Jazzy, Gazebo
Harmonic, and the TurtleBot 4 simulation — is installed into a local,
self-contained [pixi](https://pixi.sh) environment using the
[RoboStack](https://robostack.github.io) conda packages. Gazebo's GUI runs
natively on your desktop, no `--x11` tricks required, and your files are just
your files (no `chown -R` after the workshop).

## Prerequisites

1. Install pixi: `curl -fsSL https://pixi.sh/install.sh | sh`
   (Windows PowerShell: `powershell -c "irm https://pixi.sh/install.ps1 | iex"`)
2. **Windows only:** install Visual Studio 2022 (Community is fine) or the
   Build Tools, with the *Desktop development with C++* workload. It's needed
   to compile the TurtleBot 4 packages.

## Quick start

```bash
git clone <this repo>
cd <this repo>

pixi run build     # fetches sources into ./src and colcon-builds them
pixi run sim       # launches the TurtleBot 4 maze world in Gazebo
```

The first `pixi run build` downloads the whole ROS 2 Jazzy desktop + Gazebo
Harmonic stack (a few GB) and compiles the TurtleBot 4 / Create 3 packages
from source, so give it a while — comparable to the `docker build` path in the
original workshop.

## Workshop workflow (Docker → pixi cheat sheet)

| Docker workshop                                                        | pixi edition                    |
| ---------------------------------------------------------------------- | ------------------------------- |
| `docker pull ...` / `docker build . -t tb4`                            | `pixi run build`                |
| `rocker --x11 --devices=/dev/dri tb4 bash`                             | `pixi shell`                    |
| `--volume .../workshop:/opt/ros/overlay_ws/src/workshop`               | put your code in `./src/workshop` |
| `source ./install/setup.bash`                                          | automatic in `pixi shell`/tasks |
| `colcon build`                                                         | `pixi run build` (or `colcon build` inside `pixi shell`) |
| `ros2 launch turtlebot4_gz_bringup turtlebot4_gz.launch.py world:=maze`| `pixi run sim`                  |
| teleop keyboard command                                                | `pixi run teleop`               |
| velocity publisher command                                             | `pixi run drive-circle`         |
| `sudo chown -R $(whoami) ./workshop/`                                  | not needed 🎉                   |

Open extra terminals the same way you'd `docker exec` into the container:
just run `pixi shell` in the project directory again. Every shell has ROS 2,
Gazebo, and your built overlay sourced and ready (`ros2 topic list`,
`ros2 run tb4_toy toy_node`, etc.).

Working through the [ROS 2 Jazzy CLI tutorials](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools.html)
also works out of the box inside `pixi shell`.

## Writing your workshop code

Create your package under `src/workshop/` (or clone the finished example):

```bash
cd src/workshop
git clone https://github.com/kscottz/tb4_toy.git
cd ../..
pixi run build
pixi shell
ros2 run tb4_toy toy_node
ros2 service call /do_loopy std_srvs/Trigger '{}'
```

Files are created as your own user on your own filesystem — the Docker
permissions section of the original README does not apply here.

## How it maps to the Dockerfile

- `FROM ros:jazzy` + `ros-jazzy-desktop` → `ros-jazzy-desktop` from the
  `robostack-jazzy` channel.
- `apt install gz-harmonic` + `ros-jazzy-ros-gz` → `ros-jazzy-ros-gz`, which
  pulls Gazebo Harmonic (gz-sim 8) from conda-forge on all three OSes.
- `git clone turtlebot4_simulator -b jazzy` + `rosdep install` →
  `pixi run setup` clones `turtlebot4_simulator`, `turtlebot4`, `create3_sim`
  and `irobot_create_msgs` (the packages rosdep would install as debs but that
  RoboStack doesn't ship) into `./src`; their remaining binary dependencies
  (nav2, slam_toolbox, robot_localization, xacro, ...) are declared in
  `pixi.toml`.
- `colcon build --symlink-install` → `pixi run build`.
- entrypoint sourcing of the overlay → pixi activation scripts
  (`scripts/activate.sh` / `scripts/activate.bat`).

If a build complains about a missing dependency, run
`pixi run deps-check` to see what rosdep thinks is missing, then
`pixi add ros-jazzy-<name>` (RoboStack naming: underscores become dashes).

## Platform notes

- **Linux** is the best-supported platform, same as upstream ROS. If Gazebo's
  GUI or the simulated lidar misbehaves on machines without a discrete GPU,
  uncomment the software-rendering exports at the bottom of
  `scripts/activate.sh` (this mirrors the "no fancy graphics card" tuning the
  Docker container does).
- **macOS** (Intel and Apple Silicon) runs natively — no X11/XQuartz. Gazebo
  GUI support on macOS is newer and some rendering-based sensors have had
  Metal-related quirks; if the full sim is unstable, you can still do all the
  ROS 2 CLI/tutorial parts, run the sim headless (`world:=maze` with
  `gui:=false`-style args), or use RViz2.
- **Windows** runs natively too (no WSL required), but it is the least-tested
  combination for Gazebo. Keep the project in a short path (e.g. `C:\ws`) to
  avoid Windows path-length limits during the colcon build. If native Windows
  gives you trouble, WSL2 + the Linux instructions is a reliable fallback.

## Layout

```
pixi.toml                    # environment + tasks (the "Dockerfile")
scripts/setup_workspace.py   # clones simulator sources into ./src
scripts/clean_workspace.py   # removes build/ install/ log/
scripts/activate.sh|.bat     # auto-source the colcon overlay
src/                         # simulator sources + your workshop code
```
