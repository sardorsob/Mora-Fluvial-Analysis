"""Pick out dates, instrument IDs and other hints from known filename patterns.

These are hints to check against the file contents and field records, not
verified trial metadata. This module doesn't compare or reconcile those sources.
"""

from pathlib import Path
import re


SOURCE_TYPES = {
    "livereading": "live_reading",
    "livereadings": "live_reading",
    "log": "log",
    "general": "general",
}


def _normalize_bank(value):
    key = re.sub(r"[-_]", "", value.lower())
    return {"riverleft": "river_left", "riverright": "river_right"}.get(key)


def parse_filename(path):
    """Return fields suggested by a known filename pattern, or an empty dict."""

    name = Path(path).stem
    lower = name.lower()

    # VuSitu export names include the date, time and report type.
    vendor = re.search(
        r"v(?:u)?situ_(livereadings|log)_(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})",
        lower,
    )
    if vendor:
        source, y, m, d, hh, mm, ss = vendor.groups()
        return {
            "date": f"{y}{m}{d}",
            "time": f"{hh}{mm}{ss}",
            "source_type": SOURCE_TYPES[source],
        }

    # Project filenames vary. Read optional parts in order, then treat the next
    # part as the site label; field records still need to confirm that guess.
    parts = re.split(r"[_\s]+", name)
    if not parts or not re.fullmatch(r"\d{8}", parts[0]):
        return {}

    out = {"date": parts[0]}
    index = 1

    if index < len(parts) and re.fullmatch(r"\d{6}", parts[index]):
        out["time"] = parts[index]
        index += 1

    if index < len(parts):
        token = parts[index].lower()
        source = SOURCE_TYPES.get(token)
        general = re.fullmatch(r"general(\d+)", token)
        if source:
            out["source_type"] = source
            index += 1
        elif general:
            out["source_type"] = "general"
            out["instrument_id"] = general.group(1)
            index += 1

    if index < len(parts) and re.fullmatch(r"\d+", parts[index]):
        out["instrument_id"] = parts[index]
        index += 1

    if index < len(parts):
        out["site"] = parts[index]
        index += 1

    if index < len(parts):
        bank = _normalize_bank(parts[index])
        if bank:
            out["bank"] = bank

    return out
