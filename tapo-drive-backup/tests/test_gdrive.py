"""Tests for backup.gdrive — upload and rotation logic (mocked Drive API)."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from backup.gdrive import upload_file, list_drive_files, rotate_drive_folder


def _make_svc_for_list(file_list):
    """
    Return a mock Drive service whose files().list(...).execute() returns
    file_list in one page.  Uses attribute-chain assignment so that the
    mock setup itself never *calls* delete() or other methods.
    """
    svc = MagicMock()
    # Access via return_value chain to avoid recording spurious calls.
    svc.files.return_value.list.return_value.execute.return_value = {
        'files': file_list,
        'nextPageToken': None,
    }
    svc.files.return_value.delete.return_value.execute.return_value = {}
    return svc


class TestUploadFile(unittest.TestCase):

    def _write_tmp_file(self, tmpdir, name='clip.mp4', content=b'data'):
        p = Path(tmpdir) / name
        p.write_bytes(content)
        return p

    def setUp(self):
        # Patch MediaFileUpload so it never opens a real file handle,
        # preventing Windows "file in use" errors during tempdir cleanup.
        patcher = patch('backup.gdrive.MediaFileUpload', return_value=MagicMock())
        self.mock_media = patcher.start()
        self.addCleanup(patcher.stop)

    def test_successful_upload_returns_file_id(self):
        svc = MagicMock()
        svc.files.return_value.create.return_value.execute.return_value = {
            'id': 'abc123', 'name': 'clip.mp4', 'size': '1000',
        }
        with tempfile.TemporaryDirectory() as tmp:
            clip = self._write_tmp_file(tmp)
            result = upload_file(svc, clip, folder_id='folder1')
        self.assertEqual(result, 'abc123')

    def test_remote_name_used_in_metadata(self):
        """remote_name overrides the local filename in the Drive metadata."""
        svc = MagicMock()
        svc.files.return_value.create.return_value.execute.return_value = {
            'id': 'xyz', 'name': 'Front Door 2024-01-14 19-00-00.mp4', 'size': '500',
        }
        with tempfile.TemporaryDirectory() as tmp:
            clip = self._write_tmp_file(tmp, name='2024-01-14 19-00-00.mp4')
            upload_file(svc, clip, folder_id='f1',
                        remote_name='Front Door 2024-01-14 19-00-00.mp4')
        call_kwargs = svc.files.return_value.create.call_args.kwargs
        self.assertEqual(call_kwargs['body']['name'],
                         'Front Door 2024-01-14 19-00-00.mp4')

    def test_rate_limit_retries_then_succeeds(self):
        from googleapiclient.errors import HttpError
        resp = MagicMock()
        resp.status = 429
        http_err = HttpError(resp, b'rate limit')

        svc = MagicMock()
        svc.files.return_value.create.return_value.execute.side_effect = [
            http_err,
            {'id': 'retried_id', 'name': 'clip.mp4', 'size': '500'},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            clip = self._write_tmp_file(tmp)
            with patch('backup.gdrive.time.sleep'):
                result = upload_file(svc, clip, folder_id='f1', retries=3)
        self.assertEqual(result, 'retried_id')

    def test_non_retryable_http_error_returns_none(self):
        from googleapiclient.errors import HttpError
        resp = MagicMock()
        resp.status = 400
        svc = MagicMock()
        svc.files.return_value.create.return_value.execute.side_effect = (
            HttpError(resp, b'bad request')
        )
        with tempfile.TemporaryDirectory() as tmp:
            clip = self._write_tmp_file(tmp)
            result = upload_file(svc, clip, folder_id='f1')
        self.assertIsNone(result)

    def test_all_retries_exhausted_returns_none(self):
        from googleapiclient.errors import HttpError
        resp = MagicMock()
        resp.status = 429
        svc = MagicMock()
        svc.files.return_value.create.return_value.execute.side_effect = (
            HttpError(resp, b'quota')
        )
        with tempfile.TemporaryDirectory() as tmp:
            clip = self._write_tmp_file(tmp)
            with patch('backup.gdrive.time.sleep'):
                result = upload_file(svc, clip, folder_id='f1', retries=2)
        self.assertIsNone(result)


class TestListDriveFiles(unittest.TestCase):

    def test_returns_files_with_int_size(self):
        svc = _make_svc_for_list([
            {'id': '1', 'name': 'a.mp4', 'size': '1000', 'createdTime': 'T1'},
            {'id': '2', 'name': 'b.mp4', 'size': '2000', 'createdTime': 'T2'},
        ])
        files = list_drive_files(svc, 'folder1')
        self.assertEqual(len(files), 2)
        self.assertIsInstance(files[0]['size'], int)
        self.assertEqual(files[0]['size'], 1000)

    def test_handles_missing_size(self):
        svc = _make_svc_for_list([
            {'id': '1', 'name': 'a.mp4', 'createdTime': 'T1'},
        ])
        files = list_drive_files(svc, 'folder1')
        self.assertEqual(files[0]['size'], 0)


class TestRotateDriveFolder(unittest.TestCase):

    def test_under_cap_no_deletion(self):
        svc = _make_svc_for_list([
            {'id': '1', 'name': 'a.mp4', 'size': '1000',
             'createdTime': '2024-01-01T00:00:00Z'},
        ])
        deleted = rotate_drive_folder(svc, 'folder1', cap_bytes=10 * 1024 ** 3)
        self.assertEqual(deleted, 0)
        svc.files.return_value.delete.assert_not_called()

    def test_over_cap_deletes_oldest_first(self):
        gb = 1024 ** 3
        files = [
            {'id': '1', 'name': 'oldest.mp4', 'size': str(10 * gb),
             'createdTime': '2024-01-01T00:00:00Z'},
            {'id': '2', 'name': 'middle.mp4', 'size': str(10 * gb),
             'createdTime': '2024-01-02T00:00:00Z'},
            {'id': '3', 'name': 'newest.mp4', 'size': str(10 * gb),
             'createdTime': '2024-01-03T00:00:00Z'},
        ]
        svc = _make_svc_for_list(files)
        deleted = rotate_drive_folder(svc, 'folder1', cap_bytes=12 * gb)
        # Total 30 GB, cap 12 GB → must delete 20 GB (oldest + middle)
        self.assertEqual(deleted, 20 * gb)
        self.assertEqual(svc.files.return_value.delete.call_count, 2)

    def test_exactly_at_cap_no_deletion(self):
        gb = 1024 ** 3
        svc = _make_svc_for_list([
            {'id': '1', 'name': 'a.mp4', 'size': str(12 * gb),
             'createdTime': '2024-01-01T00:00:00Z'},
        ])
        deleted = rotate_drive_folder(svc, 'folder1', cap_bytes=12 * gb)
        self.assertEqual(deleted, 0)
        svc.files.return_value.delete.assert_not_called()


class TestUploadState(unittest.TestCase):

    def test_mark_and_check(self):
        from backup.state import UploadState
        with tempfile.TemporaryDirectory() as tmp:
            state = UploadState(path=str(Path(tmp) / 'state.json'))
            self.assertFalse(state.is_uploaded('clip.mp4'))
            state.mark_uploaded('clip.mp4')
            self.assertTrue(state.is_uploaded('clip.mp4'))

    def test_persists_across_instances(self):
        from backup.state import UploadState
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / 'state.json')
            s1 = UploadState(path=path)
            s1.mark_uploaded('a.mp4')
            s2 = UploadState(path=path)
            self.assertTrue(s2.is_uploaded('a.mp4'))
            self.assertFalse(s2.is_uploaded('b.mp4'))

    def test_no_duplicate_entries(self):
        import json
        from backup.state import UploadState
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / 'state.json')
            s = UploadState(path=path)
            s.mark_uploaded('a.mp4')
            s.mark_uploaded('a.mp4')
            with open(path) as f:
                data = json.load(f)
            self.assertEqual(data['uploaded'].count('a.mp4'), 1)


if __name__ == '__main__':
    unittest.main()
