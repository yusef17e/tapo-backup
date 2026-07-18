import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def download_clips(tapo_cli_path, download_dir, lookback_days):
    """
    Invoke tapo-cli download-videos via subprocess.

    Returns:
        (clips, exit_code) where clips is a sorted list of Path objects
        for every .mp4 found under download_dir (including pre-existing ones).

    Never raises — errors are logged and exit_code is returned for the caller
    to decide how to handle them.
    """
    os.makedirs(download_dir, exist_ok=True)

    cmd = [
        sys.executable,
        os.path.expanduser(tapo_cli_path),
        'download-videos',
        '--days', str(lookback_days),
        '--path', str(download_dir),
        '--overwrite', '0',
    ]

    logger.info("Running tapo-cli: %s", ' '.join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600,
        )
    except subprocess.TimeoutExpired:
        logger.error("tapo-cli timed out after 1 hour")
        # TODO: add email/webhook alerting here for download failures
        return [], -1
    except Exception as exc:
        logger.error("Failed to launch tapo-cli: %s", exc, exc_info=True)
        # TODO: add email/webhook alerting here for download failures
        return [], -1

    if result.stdout:
        logger.debug("tapo-cli stdout:\n%s", result.stdout)
    if result.stderr:
        logger.debug("tapo-cli stderr:\n%s", result.stderr)

    if result.returncode != 0:
        logger.error(
            "tapo-cli exited %d. stdout: %.500s",
            result.returncode,
            result.stdout,
        )
        # TODO: add email/webhook alerting here for download failures

    clips = sorted(Path(download_dir).rglob('*.mp4'))
    logger.info("Found %d clip(s) under %s", len(clips), download_dir)
    return clips, result.returncode
