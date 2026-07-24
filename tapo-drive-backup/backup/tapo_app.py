"""
Tapo footage downloader via BlueStacks + ADB.
Drives the Tapo app UI to pull SD card recordings from scheduled windows.

TODO markers indicate steps that need UI element IDs confirmed by running
the emulator and inspecting the app with:
    python -m uiautomator2 screenshot
    d.dump_hierarchy()
"""
import logging
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

BLUESTACKS_ADB_PORT = "5555"       # default BlueStacks ADB port
TAPO_PACKAGE       = "com.tplink.tapo"

# Paths where Tapo app saves downloaded clips on the emulator
EMULATOR_DOWNLOAD_PATHS = [
    "/sdcard/DCIM/Tapo",
    "/sdcard/Movies/Tapo",
    "/sdcard/Pictures/Tapo",
]


# ── ADB helpers ────────────────────────────────────────────────────────────

def _adb(*args, check=True):
    result = subprocess.run(["adb", *args], capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"adb {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _connect():
    import uiautomator2 as u2
    _adb("connect", f"127.0.0.1:{BLUESTACKS_ADB_PORT}", check=False)
    d = u2.connect(f"127.0.0.1:{BLUESTACKS_ADB_PORT}")
    logger.info("Emulator connected: %s", d.device_info.get("productName", "?"))
    return d


# ── App navigation ─────────────────────────────────────────────────────────

def _launch(d):
    """Cold-start Tapo app, wait for home screen."""
    d.app_start(TAPO_PACKAGE, stop=True)
    time.sleep(6)
    # TODO: if login screen appears (session expired), handle re-login here


def _go_home(d):
    """Return to Tapo home screen between cameras."""
    d.press("back")
    d.press("back")
    time.sleep(1)


def _open_camera(d, app_name):
    """Tap camera card by its name as shown in the Tapo app."""
    # TODO: confirm element type after inspecting hierarchy
    # Might be: d(text=app_name) or d(description=app_name) or d(resourceId="...")
    el = d(text=app_name)
    if not el.exists(timeout=5):
        raise RuntimeError(f"Camera '{app_name}' not found on home screen")
    el.click()
    time.sleep(3)


def _open_playback(d):
    """Tap the Playback tab/button inside the camera view."""
    # TODO: inspect actual element — common candidates:
    #   d(text="Playback")
    #   d(description="Playback")
    #   d(resourceId="com.tplink.tapo:id/playback_tab")
    d(text="Playback").click()
    time.sleep(4)


def _select_date(d, date: datetime):
    """Navigate playback timeline to a specific date."""
    # TODO: the Tapo app shows a calendar or date strip above the timeline.
    # Need to swipe/tap to reach the correct date.
    # Placeholder: assumes we're already on today; swipe left for past dates.
    days_back = (datetime.now().date() - date.date()).days
    for _ in range(days_back):
        d.swipe(0.8, 0.5, 0.2, 0.5, duration=0.3)  # swipe left = earlier date
        time.sleep(1)


def _tap_download_for_window(d, start_hhmm: str, end_hhmm: str):
    """
    On the playback timeline, select the clip(s) in [start_hhmm, end_hhmm]
    and tap the download button.

    TODO: this is the most UI-dependent step and needs hands-on testing.
    The Tapo app timeline may require:
      - long-press to start selection
      - drag to extend the range
      - tap a download icon that appears
    Alternatively, individual clips may have their own download buttons.
    """
    logger.info("Selecting window %s – %s (TODO: implement UI steps)", start_hhmm, end_hhmm)
    # Placeholder — fill in after inspecting the emulator UI
    time.sleep(2)


def _wait_for_downloads(d, timeout=120):
    """Wait for any in-progress downloads to finish."""
    # TODO: watch for a progress indicator or notification to disappear
    # Simple approach: fixed wait based on expected clip length
    logger.info("Waiting %ds for downloads to complete...", timeout)
    time.sleep(timeout)


# ── File extraction ────────────────────────────────────────────────────────

def _pull_from_emulator(cam_dir: Path) -> list[Path]:
    """Pull downloaded MP4s from emulator storage to Windows."""
    pulled = []
    for epath in EMULATOR_DOWNLOAD_PATHS:
        result = subprocess.run(
            ["adb", "pull", epath, str(cam_dir)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            logger.info("Pulled from emulator: %s", epath)
    for f in cam_dir.rglob("*.mp4"):
        pulled.append(f)
    return pulled


def _clear_emulator_downloads():
    """Delete Tapo downloads from emulator to keep its storage clean."""
    for epath in EMULATOR_DOWNLOAD_PATHS:
        _adb("shell", "rm", "-rf", epath, check=False)


# ── Per-camera download ────────────────────────────────────────────────────

def _download_camera(d, name, app_name, schedules, download_dir, lookback_days):
    cam_dir = Path(download_dir) / name
    cam_dir.mkdir(parents=True, exist_ok=True)

    try:
        _open_camera(d, app_name)
        _open_playback(d)
    except Exception as exc:
        logger.error("[%s] Could not open playback: %s", name, exc)
        _go_home(d)
        return []

    for days_ago in range(lookback_days + 1):
        date = datetime.now() - timedelta(days=days_ago)
        day_name = date.strftime("%A").lower()
        if day_name not in schedules:
            continue
        window = schedules[day_name]
        logger.info("[%s] Downloading %s %s–%s", name, date.strftime("%Y-%m-%d"),
                    window["start"], window["end"])
        try:
            _select_date(d, date)
            _tap_download_for_window(d, window["start"], window["end"])
            _wait_for_downloads(d)
        except Exception as exc:
            logger.warning("[%s] Failed on %s: %s", name, date.date(), exc)

    _go_home(d)
    clips = _pull_from_emulator(cam_dir)
    logger.info("[%s] Pulled %d clip(s)", name, len(clips))
    return clips


# ── Public interface ───────────────────────────────────────────────────────

def download_clips(cameras, download_dir, lookback_days, schedules):
    """
    Download SD card footage via Tapo app in BlueStacks.
    Drop-in replacement for backup/tapo.py once UI TODOs are filled in.

    cameras: dict of {display_name: {ip, user, app_name (optional)}}
    schedules: dict of {weekday: {start, end}}
    """
    try:
        d = _connect()
        _launch(d)
    except Exception as exc:
        logger.error("Cannot connect to BlueStacks emulator: %s", exc)
        logger.error("Make sure BlueStacks is running and ADB is enabled in its settings.")
        return []

    _clear_emulator_downloads()

    clips = []
    for name, cam in cameras.items():
        app_name = cam.get("app_name", name)  # falls back to config name if not set
        try:
            clips.extend(_download_camera(d, name, app_name, schedules, download_dir, lookback_days))
        except Exception as exc:
            logger.error("Camera task error [%s]: %s", name, exc)

    return sorted(clips)
