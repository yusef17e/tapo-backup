"""Time-window schedule filter for clip uploads."""
import datetime
from pathlib import Path


def clip_in_schedule(clip_path, schedules):
    """
    Return True if the clip's timestamp falls within a scheduled time window.

    Expects clip filenames in the format 'YYYY-MM-DD HH-MM-SS.mp4'.
    If the name cannot be parsed, returns True so clips with unexpected
    names are never silently discarded.

    schedules: dict mapping lowercase day names to {'start': 'HH:MM', 'end': 'HH:MM'}.
    Days not present in the dict are treated as "no recording" and return False.
    """
    stem = Path(clip_path).stem
    try:
        dt = datetime.datetime.strptime(stem, '%Y-%m-%d %H-%M-%S')
    except ValueError:
        return True  # unrecognised name → pass through rather than silently drop

    day_name = dt.strftime('%A').lower()
    if day_name not in schedules:
        return False

    window = schedules[day_name]
    clip_mins = dt.hour * 60 + dt.minute
    mins = lambda t: int(t[:2]) * 60 + int(t[3:])
    return mins(window['start']) <= clip_mins <= mins(window['end'])
