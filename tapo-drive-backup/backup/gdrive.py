import logging
import time
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/drive.file']

logger = logging.getLogger(__name__)


def get_drive_service(credentials_dir):
    """
    Load or silently refresh OAuth credentials and return a Drive API client.

    Raises RuntimeError if no valid token exists — caller should catch this
    and log clearly, since it means unattended runs will fail until
    auth_setup.py is re-run.
    """
    import os
    token_path = os.path.join(credentials_dir, 'token.json')
    creds_path = os.path.join(credentials_dir, 'credentials.json')

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as exc:
                # Token is dead — unattended runs will break until re-auth.
                logger.error(
                    "OAuth token refresh failed: %s. "
                    "Run auth_setup.py to re-authenticate.",
                    exc,
                )
                # TODO: add email/webhook alerting here for auth failures
                raise RuntimeError("OAuth token refresh failed") from exc
            with open(token_path, 'w') as f:
                f.write(creds.to_json())
        else:
            raise RuntimeError(
                f"No valid token at {token_path}. Run auth_setup.py first."
            )

    return build('drive', 'v3', credentials=creds)


def upload_file(service, local_path, folder_id, remote_name=None, retries=3):
    """
    Upload a single file to a Drive folder with retry on rate-limit errors.

    remote_name: filename to use in Drive (defaults to the local filename).
                 Pass a camera-prefixed name when multiple cameras are in use
                 so clips with identical timestamps don't collide in Drive.
    Returns the Drive file ID on success, None on failure.
    """
    name = remote_name or Path(local_path).name
    media = MediaFileUpload(str(local_path), resumable=True)
    metadata = {'name': name, 'parents': [folder_id]}

    for attempt in range(1, retries + 1):
        try:
            f = (
                service.files()
                .create(body=metadata, media_body=media, fields='id,name,size')
                .execute()
            )
            logger.info("Uploaded %s → Drive ID %s", name, f['id'])
            return f['id']
        except HttpError as exc:
            if exc.resp.status in (403, 429):
                wait = 2 ** attempt
                logger.warning(
                    "Rate-limit/quota error uploading %s (HTTP %d), "
                    "retrying in %ds (attempt %d/%d)",
                    name, exc.resp.status, wait, attempt, retries,
                )
                time.sleep(wait)
            else:
                logger.error("HTTP error uploading %s: %s", name, exc)
                return None
        except Exception as exc:
            logger.error("Unexpected error uploading %s: %s", name, exc)
            return None

    logger.error("Giving up on %s after %d attempts", name, retries)
    return None


def list_drive_files(service, folder_id):
    """
    List all files in a Drive folder (handles pagination).

    Returns a list of dicts: [{id, name, size (int), createdTime}, ...]
    """
    results = []
    page_token = None

    while True:
        response = (
            service.files()
            .list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields='nextPageToken, files(id, name, size, createdTime)',
                pageToken=page_token,
            )
            .execute()
        )
        for f in response.get('files', []):
            f['size'] = int(f.get('size', 0))
            results.append(f)
        page_token = response.get('nextPageToken')
        if not page_token:
            break

    return results


def rotate_drive_folder(service, folder_id, cap_bytes):
    """
    Delete the oldest files in the Drive folder until total size <= cap_bytes.
    Uses files().delete() to bypass trash (permanent deletion).

    Returns total bytes deleted.
    """
    files = list_drive_files(service, folder_id)
    total = sum(f['size'] for f in files)

    logger.info(
        "Drive folder before rotation: %.2f GB (%d files)",
        total / 1024 ** 3,
        len(files),
    )

    if total <= cap_bytes:
        logger.info("Under cap (%.2f GB), no rotation needed.", cap_bytes / 1024 ** 3)
        return 0

    files.sort(key=lambda f: f['createdTime'])

    bytes_deleted = 0
    for f in files:
        if total <= cap_bytes:
            break
        try:
            service.files().delete(fileId=f['id']).execute()
            total -= f['size']
            bytes_deleted += f['size']
            logger.info(
                "Deleted from Drive: %s (%.1f MB)", f['name'], f['size'] / 1024 ** 2
            )
        except HttpError as exc:
            logger.error("Failed to delete %s from Drive: %s", f['name'], exc)

    logger.info(
        "Rotation complete. Deleted %.1f MB. New total: %.2f GB",
        bytes_deleted / 1024 ** 2,
        total / 1024 ** 3,
    )
    return bytes_deleted
