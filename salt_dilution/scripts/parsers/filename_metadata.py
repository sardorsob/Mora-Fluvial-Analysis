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
    name = Path(path).stem
    lower = name.lower()

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

    parts = re.split(r"[_\s]+", name)
    if not parts or not re.fullmatch(r"\d{8}", parts[0]):
        return {}

    out = {"date": parts[0]}
    index = 1

    if index < len(parts) and re.fullmatch(r"\d{6}", parts[index]):
        out["time"] = parts[index]
        index += 1

    if index < len(parts):
        source = SOURCE_TYPES.get(parts[index].lower())
        if source:
            out["source_type"] = source
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
