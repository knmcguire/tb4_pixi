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
