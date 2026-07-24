#!/usr/bin/env python3
"""
tapo-backup pipeline:
  1. Download clips from camera SD cards (pytapo, local WiFi)
  2. Filter clips to configured schedule windows
  3. Upload new clips to friend's server via SFTP (idempotent via state.json)
"""
import datetime
import logging
import logging.handlers
import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # Load .env file if present (no-op when env vars are already set by Docker)

from backup.config import load_config
from backup.sftp import rotate_server, upload_clips
from backup.schedule import clip_in_schedule
from backup.state import UploadState
from backup.tapo_app import download_clips


def setup_logging(log_dir, level=logging.INFO):
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "backup.log")
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=5 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(fmt)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(file_handler)
    root.addHandler(console_handler)


logger = logging.getLogger(__name__)


def run_download_stage(cfg):
    """Download from all cameras. Returns list of Path objects."""
    # Guard: skip if disk is too full to safely store a night's footage
    min_free_bytes = cfg.get("min_free_disk_gb", 10) * 1024 ** 3
    download_dir = cfg["download_dir"]
    os.makedirs(download_dir, exist_ok=True)
    free = shutil.disk_usage(download_dir).free
    if free < min_free_bytes:
        logger.error(
            "Low disk space: %.1f GB free, %.1f GB required. "
            "Skipping download. Free up space or lower min_free_disk_gb in config.yaml.",
            free / 1024 ** 3,
            min_free_bytes / 1024 ** 3,
        )
        return []

    try:
        clips = download_clips(
            cameras=cfg["cameras"],
            download_dir=cfg["download_dir"],
            lookback_days=cfg["lookback_days"],
            schedules=cfg.get("schedules", {}),
        )
        return clips
    except Exception as exc:
        logger.error("Download stage failed: %s", exc, exc_info=True)
        return []


def run_filter_stage(cfg, clips):
    """Remove clips outside configured schedule windows. Returns filtered list."""
    schedules = cfg.get("schedules")
    if not schedules:
        return clips

    in_window = [c for c in clips if clip_in_schedule(c, schedules)]
    out_of_window = [c for c in clips if c not in in_window]

    if out_of_window:
        logger.info(
            "Schedule filter: %d/%d clip(s) in window; discarding %d.",
            len(in_window), len(clips), len(out_of_window),
        )
        for c in out_of_window:
            try:
                c.unlink()
            except OSError as exc:
                logger.warning("Could not delete out-of-window clip %s: %s", c, exc)

    return in_window


def run_upload_stage(cfg, clips, state):
    """Upload clips to SFTP server. Returns (uploaded_count, failed_count)."""
    server = cfg.get("server", {})
    if not server.get("host"):
        logger.warning(
            "SSH_HOST not configured — skipping upload. "
            "Set SSH_HOST (and other SSH_* vars) in .env when server is ready."
        )
        return 0, 0

    if not clips:
        logger.info("No clips to upload.")
        return 0, 0

    download_root = Path(cfg["download_dir"]).resolve()
    pending = []
    state_keys = {}

    for clip in clips:
        try:
            rel = clip.resolve().relative_to(download_root)
            key = rel.as_posix()
        except ValueError:
            key = clip.name
        state_keys[clip] = key
        if not state.is_uploaded(key):
            pending.append(clip)
        else:
            logger.debug("Skip already-uploaded: %s", key)

    if not pending:
        logger.info("All %d clip(s) already uploaded.", len(clips))
        return 0, 0

    succeeded = upload_clips(server, pending)

    uploaded = failed = 0
    retention = cfg["local_retention_days"]
    cutoff = datetime.datetime.now() - datetime.timedelta(days=retention)

    for clip in pending:
        if clip in succeeded:
            state.mark_uploaded(state_keys[clip])
            uploaded += 1
            mtime = datetime.datetime.fromtimestamp(clip.stat().st_mtime)
            if retention == 0 or mtime < cutoff:
                try:
                    clip.unlink()
                    logger.debug("Deleted local copy: %s", clip)
                except OSError as exc:
                    logger.warning("Could not delete local %s: %s", clip, exc)
        else:
            failed += 1

    if failed > 0 and uploaded == 0:
        logger.error("All %d upload(s) failed.", failed)

    logger.info("Upload stage: %d uploaded, %d failed.", uploaded, failed)
    return uploaded, failed


def run_rotation_stage(cfg):
    """Delete old footage from server. Skips if server not configured or retention_days is 0."""
    server = cfg.get("server", {})
    if not server.get("host"):
        return
    retention_days = server.get("retention_days", 0)
    if not retention_days:
        return
    try:
        deleted = rotate_server(server, retention_days)
        logger.info("Rotation stage: %d old clip(s) removed from server.", deleted)
    except Exception as exc:
        logger.error("Rotation stage failed: %s", exc, exc_info=True)


def main():
    try:
        cfg = load_config()
    except Exception as exc:
        print(f"ERROR loading config: {exc}", file=sys.stderr)
        sys.exit(1)

    setup_logging(cfg["log_dir"])
    logger.info("=== tapo-backup starting ===")

    clips = run_download_stage(cfg)
    logger.info("Download stage: %d clip(s) found.", len(clips))

    clips = run_filter_stage(cfg, clips)
    logger.info("After schedule filter: %d clip(s) to upload.", len(clips))

    os.makedirs("data", exist_ok=True)
    state = UploadState(path="data/state.json")
    uploaded, failed = run_upload_stage(cfg, clips, state)

    run_rotation_stage(cfg)

    logger.info(
        "=== Run complete: %d downloaded, %d uploaded, %d failed ===",
        len(clips), uploaded, failed,
    )


if __name__ == "__main__":
    main()
