#!/usr/bin/env python3
"""
tapo-drive-backup — daily pipeline:
  1. Download clips from Tapo Cloud via tapo-cli subprocess
  2. Upload new clips to Google Drive (idempotent via state.json)
  3. Rotate Drive folder to stay under gdrive_cap_bytes
"""
import datetime
import logging
import logging.handlers
import os
import sys
from pathlib import Path

from backup.config import load_config
from backup.gdrive import get_drive_service, rotate_drive_folder, upload_file
from backup.schedule import clip_in_schedule
from backup.state import UploadState
from backup.tapo import download_clips


def setup_logging(log_dir, level=logging.INFO):
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'backup.log')
    fmt = logging.Formatter(
        '%(asctime)s %(levelname)-8s %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
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


# ---------------------------------------------------------------------------
# Stage runners — each catches its own exceptions so a failure in one stage
# does not prevent the others from running.
# ---------------------------------------------------------------------------

def run_filter_stage(cfg, clips):
    """
    Remove clips that fall outside configured schedule windows.
    Out-of-window local files are deleted immediately to free disk space.
    Returns the filtered list (all clips if no schedules are configured).
    """
    schedules = cfg.get('schedules')
    if not schedules:
        return clips

    in_window = [c for c in clips if clip_in_schedule(c, schedules)]
    out_of_window = [c for c in clips if c not in in_window]

    if out_of_window:
        logger.info(
            "Schedule filter: %d of %d clip(s) are within a time window; "
            "discarding %d outside window(s).",
            len(in_window), len(clips), len(out_of_window),
        )
        for c in out_of_window:
            try:
                c.unlink()
                logger.debug("Deleted out-of-window clip: %s", c)
            except OSError as exc:
                logger.warning("Could not delete local clip %s: %s", c, exc)

    return in_window


def run_download_stage(cfg):
    """Returns list of Path objects (may be empty on failure)."""
    try:
        clips, exit_code = download_clips(
            tapo_cli_path=cfg['tapo_cli_path'],
            download_dir=cfg['download_dir'],
            lookback_days=cfg['lookback_days'],
        )
        if exit_code != 0:
            logger.error(
                "tapo-cli exited %d — download may be incomplete. "
                "Upload/rotation will still run on existing files.",
                exit_code,
            )
            # TODO: add email/webhook alerting here
        return clips
    except Exception as exc:
        logger.error("Download stage raised unexpectedly: %s", exc, exc_info=True)
        # TODO: add email/webhook alerting here
        return []


def run_upload_stage(cfg, clips, state):
    """Returns (uploaded_count, failed_count)."""
    if not clips:
        logger.info("No clips to upload.")
        return 0, 0

    try:
        service = get_drive_service(cfg['credentials_dir'])
    except Exception as exc:
        logger.error(
            "Cannot get Drive service: %s — skipping upload stage.", exc
        )
        # TODO: add email/webhook alerting here
        return 0, 0

    retention = cfg['local_retention_days']
    cutoff = datetime.datetime.now() - datetime.timedelta(days=retention)
    uploaded = failed = 0
    download_root = Path(cfg['download_dir']).resolve()

    for clip in clips:
        # Use the relative path as the state key so two cameras with clips at
        # the same timestamp don't collide (e.g. Cam1/date/19-00-00.mp4 vs
        # Cam2/date/19-00-00.mp4 are distinct entries).
        try:
            rel = clip.resolve().relative_to(download_root)
            state_key = rel.as_posix()  # always forward-slash, OS-independent
            parts = rel.parts
            # Drive filename: "CameraAlias YYYY-MM-DD HH-MM-SS.mp4"
            remote_name = f"{parts[0]} {parts[-1]}" if len(parts) >= 3 else clip.name
        except ValueError:
            state_key = clip.name
            remote_name = clip.name

        if state.is_uploaded(state_key):
            logger.debug("Skipping already-uploaded: %s", state_key)
            continue

        file_id = upload_file(service, clip, cfg['gdrive_folder_id'], remote_name=remote_name)
        if file_id:
            state.mark_uploaded(state_key)
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
        # TODO: add email/webhook alerting here

    logger.info("Upload stage: %d uploaded, %d failed.", uploaded, failed)
    return uploaded, failed


def run_rotation_stage(cfg):
    """Returns bytes deleted (0 on error or nothing to delete)."""
    try:
        service = get_drive_service(cfg['credentials_dir'])
        return rotate_drive_folder(
            service, cfg['gdrive_folder_id'], cfg['gdrive_cap_bytes']
        )
    except Exception as exc:
        logger.error("Rotation stage failed: %s", exc, exc_info=True)
        return 0


# ---------------------------------------------------------------------------

def main():
    try:
        cfg = load_config()
    except Exception as exc:
        print(f"ERROR loading config.yaml: {exc}", file=sys.stderr)
        sys.exit(1)

    setup_logging(cfg['log_dir'])
    logger.info("=== tapo-drive-backup starting ===")

    clips = run_download_stage(cfg)
    logger.info("Download stage: %d clip(s) found.", len(clips))

    clips = run_filter_stage(cfg, clips)
    logger.info("After schedule filter: %d clip(s) to upload.", len(clips))

    state = UploadState()
    uploaded, failed = run_upload_stage(cfg, clips, state)

    bytes_deleted = run_rotation_stage(cfg)

    logger.info(
        "=== Run complete: %d clips found, %d uploaded, %d failed, "
        "%.1f MB rotated ===",
        len(clips),
        uploaded,
        failed,
        bytes_deleted / 1024 ** 2,
    )


if __name__ == '__main__':
    main()
