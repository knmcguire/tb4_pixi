# ROSCon 2025 Intro to ROS Workshop - pixi edition

> [!WARNING] 
> 
> -- There are still reported bugs so make sure to report any issues you encounter as a ticket here as "issues" --

A cross-platform (Linux, Windows) replacement for the[turtlebot4_docker](https://github.com/kscottz/turtlebot4_docker) container.
Instead of Docker + rocker + X11 forwarding, everything (ROS 2 Jazzy, Gazebo Harmonic, and the TurtleBot 4 simulation) is installed into a local, self-contained [pixi](https://pixi.sh) environment using the[RoboStack](https://robostack.github.io) conda packages. Gazebo's GUI runs natively on your desktop.

## Prerequisites


You should have these operating system on your laptop. This is ranked from preferred to risky.

* Preferred (this will definitely work):
  * Ubuntu 24.04 Native install
* Less preferred (will most likely work): 
  * Ubuntu 26.04 Native install
  * WSL with Ubuntu 24.04 on Windows 11
* Little risky (will need some attention and potentially additional help):
  * Windows 11
* Risky (if you are brave and AI credits to spare):
  * MacOS (but mind that we will not be able to help out much here)

Let us know in the issues here if you are having issues with your system

Pre-install instructions:

1. Install pixi: https://pixi.prefix.dev/latest/installation/ 
2. Install Visual Studio Code: https://code.visualstudio.com/ (if you are using WSL make sure to install the Remote development extension)
3. **Windows only:** install Visual Studio 2022 (Community is fine) or the
   Build Tools, with the *Desktop development with C++* workload. It's needed
   to compile the TurtleBot 4 packages.

## Installation

### Ubuntu 24.04 (or 26.04)

```bash
git clone https://github.com/knmcguire/tb4_pixi
cd https://github.com/knmcguire/tb4_pixi

pixi install      
pixi run sim       
```

### WSL on Windows 11 (Ubuntu 24.04)

First in powershell make a new WSL instance:

```powershell
wsl --install -d Ubuntu-26.04 --name wsl-u2404-rosconworkshop 
```

Then open up the new wsl by powershell: 

```powershell
wsl -d wsl-u2404-rosconworkshop
```

You can also find 'wsl-u2404-rosconworkshop' as app, or open op a 'wsl-u2404-rosconworkshop' tab in the windows terminal.

once WSL is installed and opened, you can install pixi and follow the Ubuntu installation instructions

### Windows 11 (Use with caution)

Mind that Windows 11 native install of pixi of the workshop does not work super ideal yet, but if WSL2 does not work out for you than that is a path that is also avaible. It just has different instructions. 

```cmd
git clone https://github.com/knmcguire/tb4_pixi
cd https://github.com/knmcguire/tb4_pixi

pixi run setup
pixi run build-fix
```

On Windows, you need to run Gazebo server, robot stack, and GUI in separate terminals:

```powershell
# Terminal 1
pixi run sim-server

# Terminal 2
pixi run sim-robot

# Terminal 3
pixi run sim-gui

# Terminal 4 (/clock bridge)
pixi run clock-bridge
```

## Test out workshop code

Please follow the instructions in the presentation, but if you just want to test out the workshop code that is possible with the finished example:

```bash
# In your pixi directory e.g. ~/code/tb4_pixi
mkdir -p src/
cd src/
git clone https://github.com/kscottz/tb4_toy.git
cd ../..
pixi shell  # Source the ROS workspace
colcon build --merge-install --packages-select tb4_toy
ros2 run tb4_toy toy_node
ros2 service call /do_loopy std_srvs/Trigger '{}'
```

## Support

Make sure to file a ticket (aka making an issue here) if you need any help! Make sure to give us the following information:

* The operating system
* The error from the terminal
* The generated pixi.lock file 
* The ROS log files with the errors

### Troubles shooting

#### Windows improper cleanup

On some Windows setups, `Ctrl+C` does not fully tear down all child processes
spawned by `ros2 launch` / Gazebo, leaving background `gz`/ROS processes alive.
If that happens, run:

```powershell
pixi run stop-sim
```

This kills known TurtleBot 4 simulator process trees started by this workspace.

## Disclaimer

This repo has been generated with assistence of Github Copilot Pro
