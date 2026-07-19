@echo off
rem Sourced automatically by pixi on shell/task activation (Windows).
rem Sources the colcon overlay if it has been built; otherwise a no-op.

if exist "%PIXI_PROJECT_ROOT%\install\setup.bat" (
    call "%PIXI_PROJECT_ROOT%\install\setup.bat"
)

rem Work around FastDDS shared-memory lock/mutex failures on Windows.
set "FASTDDS_BUILTIN_TRANSPORTS=UDPv4"

rem Gazebo resource lookup paths (worlds/models/assets).
set "GZ_SIM_RESOURCE_PATH=%CONDA_PREFIX%\Library\share\turtlebot4_gz_bringup\worlds;%CONDA_PREFIX%\Library\share\irobot_create_gz_bringup\worlds;%CONDA_PREFIX%\Library\share;%GZ_SIM_RESOURCE_PATH%"

rem Gazebo GUI plugin lookup paths (TurtleBot4/Create3 UI plugins).
set "GZ_GUI_PLUGIN_PATH=%CONDA_PREFIX%\Library\share\turtlebot4_gz_gui_plugins\lib;%CONDA_PREFIX%\Library\share\irobot_create_gz_plugins\lib;%GZ_GUI_PLUGIN_PATH%"

rem Gazebo system plugins on Windows can be in both bin and lib (e.g. gz_ros2_control-system.dll).
set "GZ_SIM_SYSTEM_PLUGIN_PATH=%CONDA_PREFIX%\Library\bin;%CONDA_PREFIX%\Library\lib;%GZ_SIM_SYSTEM_PLUGIN_PATH%"
