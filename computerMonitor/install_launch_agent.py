#!/usr/bin/env python3
"""Install or remove the per-user macOS LaunchAgent for background.py."""

import argparse
import os
import plistlib
import subprocess
import sys
from pathlib import Path


LABEL = "com.vobot.computermonitor"
PROJECT_DIR = Path(__file__).resolve().parent
SCRIPT = PROJECT_DIR / "background.py"
PYTHON = PROJECT_DIR / "env" / "bin" / "python"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
LOG_DIR = Path.home() / "Library" / "Logs"
DOMAIN = f"gui/{os.getuid()}"


def main():
    parser = argparse.ArgumentParser(description="Manage the Vobot Computer Monitor LaunchAgent.")
    parser.add_argument("action", nargs="?", choices=("install", "uninstall"), default="install")
    parser.add_argument("--log", action="store_true", help="enable application logging to ~/Library/Logs")
    args = parser.parse_args()

    if args.action == "uninstall":
        subprocess.run(["launchctl", "bootout", DOMAIN, str(PLIST_PATH)], check=False)
        PLIST_PATH.unlink(missing_ok=True)
        print("LaunchAgent removed.")
        return 0

    if not PYTHON.is_file():
        print(f"Python environment not found: {PYTHON}\nCreate it and install requirements first.", file=sys.stderr)
        return 1

    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    if args.log:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    # Allow rerunning the installer to replace an already loaded definition.
    subprocess.run(["launchctl", "bootout", DOMAIN, str(PLIST_PATH)], check=False)
    program_arguments = [str(PYTHON), str(SCRIPT)]
    if args.log:
        program_arguments.append("--log")
    plist = {
        "Label": LABEL,
        "ProgramArguments": program_arguments,
        "WorkingDirectory": str(PROJECT_DIR),
        "RunAtLoad": True,
        "KeepAlive": True,
    }
    with PLIST_PATH.open("wb") as stream:
        plistlib.dump(plist, stream)
    subprocess.run(["launchctl", "bootstrap", DOMAIN, str(PLIST_PATH)], check=True)
    print(f"LaunchAgent installed and started: {PLIST_PATH}")
    if args.log:
        print(f"Application log: {LOG_DIR / 'VobotComputerMonitor.log'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
