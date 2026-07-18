import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


async def _download_segments(cam, cam_name, cam_dir, time_correction, date_str):
    """Download all recording segments for one camera on one date. Returns list of Paths."""
    try:
        recordings = cam.getRecordingsList(date_str)
    except Exception as exc:
        logger.warning("[%s] Could not list recordings for %s: %s", cam_name, date_str, exc)
        return []

    if not recordings:
        return []

    logger.info("[%s] %d segment(s) on %s", cam_name, len(recordings), date_str)

    from pytapo.media_stream.downloader import Downloader

    clips = []
    for rec in recordings:
        start, end = rec["startTime"], rec["endTime"]
        dt = datetime.fromtimestamp(start)
        filename = dt.strftime("%Y-%m-%d %H-%M-%S") + ".mp4"
        out = cam_dir / filename

        if out.exists():
            logger.debug("[%s] Already downloaded: %s", cam_name, filename)
            clips.append(out)
            continue

        logger.info("[%s] Downloading %s...", cam_name, filename)
        try:
            dl = Downloader(cam, start, end, time_correction, str(cam_dir), 50, filename)
            async for _ in dl.download():
                pass
            clips.append(out)
            logger.info("[%s] Done: %s (%.1f MB)", cam_name, filename, out.stat().st_size / 1e6)
        except Exception as exc:
            logger.error("[%s] Download failed for %s: %s", cam_name, filename, exc)

    return clips


async def _download_camera(name, ip, cloud_password, download_dir, lookback_days):
    from pytapo import Tapo

    cam_dir = Path(download_dir) / name
    cam_dir.mkdir(parents=True, exist_ok=True)

    try:
        cam = Tapo(ip, "admin", cloud_password)
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
            clips.extend(
                await _download_segments(cam, name, cam_dir, time_correction, date_str)
            )
        except Exception as exc:
            logger.warning("[%s] Unexpected error on %s: %s", name, date_str, exc)

    return clips


def download_clips(cameras, cloud_password, download_dir, lookback_days):
    """Download SD card footage from all cameras. Returns sorted list of Path objects."""
    async def _run():
        tasks = [
            _download_camera(name, ip, cloud_password, download_dir, lookback_days)
            for name, ip in cameras.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        clips = []
        for r in results:
            if isinstance(r, Exception):
                logger.error("Camera task error: %s", r)
            else:
                clips.extend(r)
        return clips

    return sorted(asyncio.run(_run()))
