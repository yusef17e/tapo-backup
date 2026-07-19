#!/usr/bin/env python3
"""
Tapo SD Card Connection Test
=============================
Run this script on the GYM PC (must be on the same WiFi as the cameras).
It connects to each camera and lists recordings from the last 3 days.
No footage is downloaded — this is just a connectivity and listing test.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP-BY-STEP: HOW TO RUN THIS TEST ON THE GYM PC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BEFORE YOU START:
  - Make sure the gym PC is connected to the gym WiFi (same network as cameras)
  - Make sure Python is installed (python.org → Download Python 3.12)

STEP 1 — Install the required library (one-time only)
  Open Command Prompt (search "cmd" in Start menu), then type:
    pip install pytapo
  Press Enter and wait for it to finish.

STEP 2 — Verify camera IPs (optional but recommended)
  The IPs below should already be correct:
    Room 1: 192.168.0.190
    Room 2: 192.168.0.24
  To double-check: open the Tapo app → tap a camera → gear icon → Device Info → IP Address

STEP 3 — Run the script
  In Command Prompt, navigate to this folder:
    cd "C:/path/to/TapoBackup"         (replace with the actual folder path)
  Then run:
    python test_pytapo.py
  Press Enter.

STEP 4 — Enter your Tapo account credentials
  The script will ask for:
    - Your Tapo account email (the one used to log into the Tapo app)
    - Your Tapo account password (typing is hidden for security)

STEP 5 — Read the results
  ✓ GOOD result (cameras working):
      Jiu-Jitsu Room 1 (192.168.0.190)
      Connected ✓   Model: C220
      2024-07-16 : 8 segment(s) found
      2024-07-15 : 6 segment(s) found

  ✗ BAD result (connection problem):
      Could not connect: ...
      - Not on the same WiFi as the cameras
      - IP address is wrong
      - Camera is offline

WHAT THE NUMBERS MEAN:
  "X segment(s) found" = the camera has X video clips in its SD card for that day.
  A typical recording session (e.g. 7 PM - 8:40 PM) produces 8-20 segments.
  If segments > 0, the full download pipeline will work.

IF SOMETHING GOES WRONG:
  - "No module named 'pytapo'" → run Step 1 again
  - "Could not authenticate" → check your email/password
  - "Could not connect" → make sure the PC is on the gym WiFi
  - "0 segment(s)" on a day you know had recording → SD card may be full or camera offline
"""

import sys
from datetime import datetime, timedelta

try:
    from pytapo import Tapo
except ImportError:
    print("\nERROR: pytapo is not installed.")
    print("Open Command Prompt and run:  pip install pytapo")
    sys.exit(1)


# ── Camera IPs ─────────────────────────────────────────────────────────────
CAMERAS = {
    "Jiu-Jitsu Room 1": "192.168.0.190",
    "Jiu-Jitsu Room 2": "192.168.0.24",
}
# ──────────────────────────────────────────────────────────────────────────


def _try_auth(ip, user, password, cloud_pw=None):
    """Try one auth combination. Returns (cam, label) or raises."""
    kwargs = {"cloudPassword": cloud_pw} if cloud_pw else {}
    cam = Tapo(ip, user, password, **kwargs)
    cam.getDeviceInfo()  # confirms auth actually worked
    return cam


def _find_working_auth(ip, email, password):
    """Try every known auth combination. Returns (cam, description) or None."""
    attempts = [
        # (user, password, cloudPassword, description)
        ("admin",  password, password, "admin / cloud-pw / cloudPassword=cloud-pw"),
        (email,    password, password, "email / cloud-pw / cloudPassword=cloud-pw"),
        ("admin",  "admin",  password, "admin / admin    / cloudPassword=cloud-pw"),
        ("admin",  password, None,     "admin / cloud-pw / no cloudPassword"),
        ("admin",  "admin",  None,     "admin / admin    / no cloudPassword"),
    ]
    for user, pw, cpw, label in attempts:
        try:
            cam = _try_auth(ip, user, pw, cpw)
            return cam, label
        except Exception as e:
            print(f"  [ ] {label}")
            print(f"      → {type(e).__name__}: {e}")
    return None, None


def _run_camera(ip, name, email, password):
    print("─" * 55)
    print(f"  {name}  ({ip})")
    print("─" * 55)

    cam, label = _find_working_auth(ip, email, password)
    if cam is None:
        print("  Could not connect — all auth methods failed.")
        print()
        print("  Possible reasons:")
        print("  - Wrong Tapo email or password")
        print("  - PC is not on the same WiFi as the cameras")
        print("  - IP address is wrong (check Tapo app: gear → Device Info)")
        print()
        return

    info = cam.getDeviceInfo()
    model = info.get("device_model", "unknown")
    print(f"  Connected ✓   Model: {model}   Auth: {label}")
    print()

    dates = [
        (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
        for i in range(3)
    ]
    total = 0
    for date_str in dates:
        label_d = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        try:
            recordings = cam.getRecordingsList(date_str)
            count = len(recordings) if recordings else 0
            total += count
            status = f"{count} segment(s)"
            if count == 0:
                status += "  (no recording or SD card empty)"
            print(f"  {label_d} : {status}")
        except Exception as e:
            print(f"  {label_d} : could not read — {e}")

    print()
    if total > 0:
        print(f"  RESULT: {total} total segment(s) found — camera is working ✓")
    else:
        print("  RESULT: 0 segments found on all 3 days")
        print("  Check: is the SD card inserted? Has there been any recording?")
    print()


def main():
    print()
    print("=" * 55)
    print("  Tapo SD Card Connection Test")
    print("=" * 55)
    print()

    email = input("Tapo account email: ").strip()

    password = input("Tapo account password (visible so you can check for typos): ").strip()

    print()

    for name, ip in CAMERAS.items():
        _run_camera(ip, name, email, password)

    print("=" * 55)
    print("  Test complete.")
    print("=" * 55)
    print()


if __name__ == "__main__":
    main()
