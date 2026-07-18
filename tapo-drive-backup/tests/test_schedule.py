"""Tests for backup.schedule — time-window filtering."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backup.schedule import clip_in_schedule

SCHEDULES = {
    'monday':    {'start': '19:00', 'end': '20:40'},
    'tuesday':   {'start': '19:00', 'end': '20:40'},
    'wednesday': {'start': '19:00', 'end': '20:40'},
    'thursday':  {'start': '19:00', 'end': '20:40'},
    'friday':    {'start': '19:00', 'end': '20:40'},
    'sunday':    {'start': '11:00', 'end': '13:00'},
}


def _clip(name):
    return Path(f'/fake/{name}.mp4')


class TestWeekdayWindow(unittest.TestCase):
    # 2024-01-15 is a Monday

    def test_inside_window(self):
        self.assertTrue(clip_in_schedule(_clip('2024-01-15 19-30-00'), SCHEDULES))

    def test_before_window(self):
        self.assertFalse(clip_in_schedule(_clip('2024-01-15 18-59-00'), SCHEDULES))

    def test_after_window(self):
        self.assertFalse(clip_in_schedule(_clip('2024-01-15 20-41-00'), SCHEDULES))

    def test_exactly_at_start(self):
        self.assertTrue(clip_in_schedule(_clip('2024-01-15 19-00-00'), SCHEDULES))

    def test_exactly_at_end(self):
        # 8:40 PM = 20:40 — boundary is inclusive
        self.assertTrue(clip_in_schedule(_clip('2024-01-15 20-40-00'), SCHEDULES))

    def test_friday_inside_window(self):
        # 2024-01-19 is a Friday
        self.assertTrue(clip_in_schedule(_clip('2024-01-19 20-00-00'), SCHEDULES))


class TestSundayWindow(unittest.TestCase):
    # 2024-01-14 is a Sunday

    def test_inside_window(self):
        self.assertTrue(clip_in_schedule(_clip('2024-01-14 12-00-00'), SCHEDULES))

    def test_at_window_end(self):
        # 1:00 PM = 13:00 — boundary is inclusive
        self.assertTrue(clip_in_schedule(_clip('2024-01-14 13-00-00'), SCHEDULES))

    def test_before_window(self):
        self.assertFalse(clip_in_schedule(_clip('2024-01-14 10-59-00'), SCHEDULES))

    def test_after_window(self):
        self.assertFalse(clip_in_schedule(_clip('2024-01-14 13-01-00'), SCHEDULES))


class TestUnscheduledDays(unittest.TestCase):

    def test_saturday_excluded(self):
        # 2024-01-13 is a Saturday — not in schedules
        self.assertFalse(clip_in_schedule(_clip('2024-01-13 12-00-00'), SCHEDULES))

    def test_empty_schedules_always_false(self):
        self.assertFalse(clip_in_schedule(_clip('2024-01-15 19-30-00'), {}))


class TestEdgeCases(unittest.TestCase):

    def test_unparseable_name_passes_through(self):
        # Clips whose names don't match the expected format are never discarded
        self.assertTrue(clip_in_schedule(Path('/fake/unknown_clip.mp4'), SCHEDULES))

    def test_no_schedules_key_returns_false(self):
        # Calling with an empty dict → no days match → False
        self.assertFalse(clip_in_schedule(_clip('2024-01-14 12-00-00'), {}))


if __name__ == '__main__':
    unittest.main()
