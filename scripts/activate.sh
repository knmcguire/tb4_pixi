# Sourced automatically by pixi on shell/task activation (Linux & macOS).
# Replaces the Dockerfile's entrypoint hack that appends
#   source "$OVERLAY_WS/install/setup.bash"
# to /ros_entrypoint.sh. No-op until the workspace has been built.

_OVERLAY_SETUP="${PIXI_PROJECT_ROOT}/install/setup.sh"
if [ -f "${_OVERLAY_SETUP}" ]; then
  # colcon setup scripts reference unset vars; be tolerant while sourcing
  set +u 2>/dev/null || true
  . "${_OVERLAY_SETUP}"
fi
unset _OVERLAY_SETUP

# The Docker container is tuned to run on machines *without* a discrete GPU
# (that's what `--devices=/dev/dri` + its Mesa config achieve). On Linux, if
# Gazebo's GUI or the simulated lidar misbehaves on integrated/older graphics,
# uncomment the two lines below to force CPU (software) rendering:
# export LIBGL_ALWAYS_SOFTWARE=1
# export MESA_GL_VERSION_OVERRIDE=3.3

# Gazebo resource lookup paths (worlds/models/assets).
export GZ_SIM_RESOURCE_PATH="${CONDA_PREFIX}/share/turtlebot4_gz_bringup/worlds:${CONDA_PREFIX}/share/irobot_create_gz_bringup/worlds:${CONDA_PREFIX}/share${GZ_SIM_RESOURCE_PATH:+:${GZ_SIM_RESOURCE_PATH}}"

# Gazebo GUI plugin lookup paths (TurtleBot4/Create3 UI plugins).
export GZ_GUI_PLUGIN_PATH="${CONDA_PREFIX}/share/turtlebot4_gz_gui_plugins/lib:${CONDA_PREFIX}/share/irobot_create_gz_plugins/lib${GZ_GUI_PLUGIN_PATH:+:${GZ_GUI_PLUGIN_PATH}}"

# Gazebo system plugin lookup paths.
export GZ_SIM_SYSTEM_PLUGIN_PATH="${CONDA_PREFIX}/lib${GZ_SIM_SYSTEM_PLUGIN_PATH:+:${GZ_SIM_SYSTEM_PLUGIN_PATH}}"
