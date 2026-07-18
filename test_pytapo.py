#!/usr/bin/env python3
"""
Test script: connects to Tapo cameras via pytapo and lists SD card recordings.

Before running:
  pip install pytapo

HOW TO FIND YOUR CAMERA IPs:
  1. Open the Tapo app on your phone
  2. Tap a camera
  3. Tap the gear icon (top-right, Settings)
  4. Tap "Device Info"
  5. Note the IP Address (looks like 192.168.X.X)
  Do this for each camera and fill them in below.

NOTE: Run this while connected to the same WiFi as the cameras.
"""

import json
import os
import sys
from datetime import datetime, timedelta

try:
    from pytapo import Tapo
    from pytapo.auth import getCloudPassword
except ImportError:
    print("ERROR: pytapo is not installed.")
    print("Run this first:  pip install pytapo")
    sys.exit(1)


# ── FILL IN YOUR CAMERA IPs BEFORE RUNNING ────────────────────────────────
CAMERAS = {
    "Jiu-Jitsu Room 1": "192.168.0.190",   # <-- replace with real IP
    "Jiu-Jitsu Room 2": "192.168.0.24",   # <-- replace with real IP
}
# ──────────────────────────────────────────────────────────────────────────


def load_stored_email():
    config_path = os.path.expanduser("~/.tapo-cli/.config")
    try:
        with open(config_path) as f:
            return json.load(f).get("email", "")
    except Exception:
        return ""


def main():
    print("=" * 55)
    print("  Tapo SD Card Connection Test")
    print("=" * 55)

    # Check IPs have been filled in
    if any("X.X" in ip for ip in CAMERAS.values()):
        print("\nERROR: Fill in the camera IP addresses at the top")
        print("of this file before running it.")
        print("\nFind them in the Tapo app:")
        print("  Tap camera → gear icon → Device Info → IP Address")
        sys.exit(1)

    # Get credentials
    email = load_stored_email()
    if email:
        print(f"\nUsing stored account: {email}")
    else:
        email = input("\nTapo account email: ").strip()

    import getpass
    password = getpass.getpass("Tapo account password: ")

    # Use cloud credentials to get the camera's local auth password
    print("\nConnecting to Tapo cloud to get camera password...")
    try:
        cloud_pw = getCloudPassword(email, password)
        print("Got camera password ✓")
    except Exception as e:
        print(f"\nERROR: Could not authenticate: {e}")
        print("Double-check your email and password.")
        sys.exit(1)

    # Dates to check (today + last 2 days)
    dates = [
        (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
        for i in range(3)
    ]

    print()

    for name, ip in CAMERAS.items():
        print("─" * 55)
        print(f"  {name}  ({ip})")
        print("─" * 55)

        try:
            cam = Tapo(ip, "admin", cloud_pw)
            info = cam.getDeviceInfo()
            model = info.get("device_model", "unknown")
            print(f"  Connected ✓   Model: {model}\n")

            for date_str in dates:
                label = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                try:
                    recordings = cam.getRecordingsList(date_str)
                    count = len(recordings) if recordings else 0
                    print(f"  {label} : {count} segment(s) found")
                except Exception as e:
                    print(f"  {label} : could not read — {e}")

        except Exception as e:
            print(f"  Could not connect: {e}")
            print()
            print("  Possible reasons:")
            print("  - Not on the same WiFi as the cameras")
            print("  - IP address is wrong")
            print("  - Camera is offline")

        print()

    print("=" * 55)
    print("  Done.")
    print("=" * 55)


if __name__ == "__main__":
    main()
