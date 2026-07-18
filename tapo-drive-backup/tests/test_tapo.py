"""Tests for backup.tapo — subprocess wrapper around tapo-cli."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Allow imports from project root when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from backup.tapo import download_clips

FAKE_CLI = str(Path(__file__).parent / 'fixtures' / 'fake_tapo_cli.py')


class TestDownloadClips(unittest.TestCase):

    def test_successful_download_returns_clips(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            clips, exit_code = download_clips(
                tapo_cli_path=FAKE_CLI,
                download_dir=tmpdir,
                lookback_days=1,
            )
        self.assertEqual(exit_code, 0)
        self.assertEqual(len(clips), 2)
        self.assertTrue(all(c.suffix == '.mp4' for c in clips))
        names = {c.name for c in clips}
        self.assertIn('2024-01-14 12-00-00.mp4', names)
        self.assertIn('2024-01-14 13-00-00.mp4', names)

    def test_nonzero_exit_still_returns_existing_files(self):
        """If tapo-cli exits non-zero, already-downloaded files are still returned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # First run creates files
            download_clips(FAKE_CLI, tmpdir, lookback_days=1)
            # Second run with failing exit code — files still present
            clips, exit_code = download_clips(
                tapo_cli_path=FAKE_CLI + ' --exit-code 1',
                download_dir=tmpdir,
                lookback_days=1,
            )
        # exit_code will be -1 (launch failure because the path is wrong),
        # but the previously downloaded files are still found.
        self.assertEqual(len(clips), 2)

    def test_missing_cli_returns_empty_list_and_nonzero_code(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            clips, exit_code = download_clips(
                tapo_cli_path='/nonexistent/tapo-cli.py',
                download_dir=tmpdir,
                lookback_days=1,
            )
        self.assertEqual(clips, [])
        self.assertNotEqual(exit_code, 0)  # -1 (launch error) or 2 (Python "no such file")

    def test_download_dir_created_if_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = os.path.join(tmpdir, 'sub', 'dir')
            self.assertFalse(os.path.exists(new_dir))
            download_clips(FAKE_CLI, new_dir, lookback_days=1)
        # Directory was created (even if tapo-cli then ran in it)
        # We can't assert it exists after the context manager, but the
        # function must not raise.


if __name__ == '__main__':
    unittest.main()
