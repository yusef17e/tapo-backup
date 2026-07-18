import logging
import os
from pathlib import Path

import paramiko

logger = logging.getLogger(__name__)


def _ensure_remote_dir(sftp, path):
    """Create remote directory tree, silently skipping existing dirs."""
    try:
        sftp.stat(path)
        return
    except FileNotFoundError:
        pass
    parent = str(Path(path).parent).replace("\\", "/")
    if parent and parent != path:
        _ensure_remote_dir(sftp, parent)
    try:
        sftp.mkdir(path)
    except OSError:
        pass  # already exists (race or root)


def upload_clips(server_cfg, clips):
    """
    Upload clips to SFTP server. Opens one connection for all files.
    Returns set of Path objects that were successfully uploaded.
    """
    if not clips:
        return set()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs = {
        "hostname": server_cfg["host"],
        "port": int(server_cfg.get("port", 22)),
        "username": server_cfg["username"],
        "timeout": 30,
    }
    key_path = server_cfg.get("key_path")
    if key_path:
        connect_kwargs["key_filename"] = os.path.expanduser(key_path)
    else:
        connect_kwargs["password"] = server_cfg.get("password", "")

    try:
        ssh.connect(**connect_kwargs)
        logger.info("SFTP connected to %s", server_cfg["host"])
    except Exception as exc:
        logger.error("SFTP connection failed to %s: %s", server_cfg["host"], exc)
        return set()

    remote_base = server_cfg.get("remote_dir", "/tapo-footage").rstrip("/")
    succeeded = set()

    try:
        sftp = ssh.open_sftp()
        for clip in clips:
            clip = Path(clip)
            # Preserve camera subfolder under remote_base
            parts = clip.parts
            camera = parts[-2] if len(parts) >= 2 else "unknown"
            remote_dir = f"{remote_base}/{camera}"
            remote_path = f"{remote_dir}/{clip.name}"

            try:
                _ensure_remote_dir(sftp, remote_dir)
                sftp.put(str(clip), remote_path)
                logger.info("Uploaded %s → %s", clip.name, remote_path)
                succeeded.add(clip)
            except Exception as exc:
                logger.error("Upload failed for %s: %s", clip.name, exc)

        sftp.close()
    finally:
        ssh.close()

    logger.info("SFTP: %d/%d uploaded.", len(succeeded), len(clips))
    return succeeded
