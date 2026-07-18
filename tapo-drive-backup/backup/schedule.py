"""Time-window schedule filter for clip uploads."""
import datetime
from pathlib import Path


def _parse_minutes(t_str):
    """Convert 'HH:MM' string to total minutes since midnight."""
    h, m = t_str.split(':')
    return int(h) * 60 + int(m)


def clip_in_schedule(clip_path, schedules):
    """
    Return True if the clip's timestamp falls within a scheduled time window.

    Expects clip filenames in the format 'YYYY-MM-DD HH-MM-SS.mp4' (the format
    written by tapo-cli). If the name cannot be parsed, returns True so that
    clips with unexpected names are never silently discarded.

    schedules: dict mapping lowercase day names to {'start': 'HH:MM', 'end': 'HH:MM'}.
    Days not present in the dict are treated as "no recording" and return False.
    """
    stem = Path(clip_path).stem
    try:
        dt = datetime.datetime.strptime(stem, '%Y-%m-%d %H-%M-%S')
    except ValueError:
        return True  # unrecognised name → pass through rather than silently drop

    day_name = dt.strftime('%A').lower()  # 'monday', 'tuesday', ...
    if day_name not in schedules:
        return False

    window = schedules[day_name]
    clip_mins = dt.hour * 60 + dt.minute
    return _parse_minutes(window['start']) <= clip_mins <= _parse_minutes(window['end'])
