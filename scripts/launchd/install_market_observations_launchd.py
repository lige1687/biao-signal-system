#!/usr/bin/env python3
"""Install the authorized market-data refresher; retain any old plist backup."""

import os
import plistlib
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LABEL = "com.lei.market.observations"


def install() -> Path:
    target = Path.home() / "Library/LaunchAgents" / f"{LABEL}.plist"
    logs = ROOT / "logs"
    logs.mkdir(exist_ok=True)
    payload = {
        "Label": LABEL,
        "ProgramArguments": [
            sys.executable,
            str(ROOT / "scripts/launchd/refresh_market_observations.py"),
        ],
        "WorkingDirectory": str(ROOT),
        "EnvironmentVariables": {
            "PYTHONPATH": str(ROOT / "src"),
            "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/local/bin"),
        },
        "RunAtLoad": True,
        "StartInterval": 1800,
        "StandardOutPath": str(logs / "market-observations.out.log"),
        "StandardErrorPath": str(logs / "market-observations.err.log"),
    }
    if target.exists():
        target.with_name(f"{target.name}.before-{datetime.now():%Y%m%dT%H%M%S}.bak").write_bytes(
            target.read_bytes()
        )
        # Never terminate an ongoing collector to replace its scheduler.
        current = subprocess.run(
            ["launchctl", "print", f"gui/{os.getuid()}/{LABEL}"], capture_output=True, text=True
        )
        if "state = running" in current.stdout:
            raise RuntimeError("existing market refresh is running; installation left unchanged")
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{LABEL}"], capture_output=True)
    encoded = plistlib.dumps(payload)
    target.write_bytes(encoded)
    assert target.read_bytes() == encoded
    subprocess.run(["plutil", "-lint", str(target)], check=True)
    subprocess.run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(target)], check=True)
    return target


if __name__ == "__main__":
    print(install())
