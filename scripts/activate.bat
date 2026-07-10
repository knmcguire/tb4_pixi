@echo off
rem Sourced automatically by pixi on shell/task activation (Windows).
rem Sources the colcon overlay if it has been built; otherwise a no-op.

if exist "%PIXI_PROJECT_ROOT%\install\setup.bat" (
    call "%PIXI_PROJECT_ROOT%\install\setup.bat"
)
