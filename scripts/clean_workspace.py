#!/usr/bin/env python3
"""Remove colcon build artifacts (build/, install/, log/) cross-platform."""

import shutil
from pathlib import Path

root = Path(__file__).resolve().parent.parent
for name in ("build", "install", "log"):
    d = root / name
    if d.exists():
        print(f"[clean] removing {d}")
        shutil.rmtree(d, ignore_errors=True)
print("[clean] done")
