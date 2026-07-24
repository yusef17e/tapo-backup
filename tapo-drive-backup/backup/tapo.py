import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


def _download_segment(cam, start, end, time_correction, cam_dir, filename):
    from pytapo.media_stream.downloader import Downloader

    async def _run():
        dl = Downloader(cam, start, end, time_correction, str(cam_dir), 50, filename)
        async for _ in dl.download():
            pass

    asyncio.run(_run())


def _download_camera(name, ip, user, cloud_password, download_dir, lookback_days):
    from pytapo import Tapo

    cam_dir = Path(download_dir) / name
    cam_dir.mkdir(parents=True, exist_ok=True)

    try:
        cam = Tapo(ip, user, cloud_password)
        time_correction = cam.getTimeCorrection()
        logger.info("[%s] Connected to %s (time correction: %s)", name, ip, time_correction)
    except Exception as exc:
        logger.error("[%s] Cannot connect to %s: %s", name, ip, exc)
        return []

    dates = [
        (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
        for i in range(lookback_days + 1)
    ]

    clips = []
    for date_str in dates:
        try:
            recordings = cam.getRecordingsList(date_str)
        except Exception as exc:
            logger.warning("[%s] Could not list recordings for %s: %s", name, date_str, exc)
            continue

        if not recordings:
            continue

        logger.info("[%s] %d segment(s) on %s", name, len(recordings), date_str)

        for rec in recordings:
            start, end = rec["startTime"], rec["endTime"]
            dt = datetime.fromtimestamp(start)
            filename = dt.strftime("%Y-%m-%d %H-%M-%S") + ".mp4"
            out = cam_dir / filename

            if out.exists():
                logger.debug("[%s] Already downloaded: %s", name, filename)
                clips.append(out)
                continue

            logger.info("[%s] Downloading %s...", name, filename)
            try:
                _download_segment(cam, start, end, time_correction, cam_dir, filename)
                clips.append(out)
                logger.info("[%s] Done: %s (%.1f MB)", name, filename, out.stat().st_size / 1e6)
            except Exception as exc:
                logger.error("[%s] Download failed for %s: %s", name, filename, exc)

    return clips


def download_clips(cameras, cloud_password, download_dir, lookback_days):
    """Download SD card footage from all cameras. Returns sorted list of Path objects."""
    clips = []
    for name, cam in cameras.items():
        try:
            clips.extend(
                _download_camera(name, cam["ip"], cam["user"], cloud_password, download_dir, lookback_days)
            )
        except Exception as exc:
            logger.error("Camera task error [%s]: %s", name, exc)
    return sorted(clips)
