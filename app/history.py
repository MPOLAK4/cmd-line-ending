"""The small cache of recent changes (R2).

The cache is one JSON file shaped like this:

    {"next_id": 3,
     "entries": [
        {"id": 2, "time": "2026-11-21T17:30:02Z", "to": "lf",
         "files": [{"path": "/abs/a.txt", "from": "crlf"}]}
     ]}
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from app.fileio import write_atomic

MAX_ENTRIES = 50  # R2.3
ENV_VAR = "CMD_LINE_ENDING_HOME"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def cache_path() -> Path:
    """Where history.json lives (R2.2): outside the files being converted."""
    base = os.environ.get(ENV_VAR)
    folder = Path(base) if base else Path.home() / ".cmd-line-ending"
    return folder / "history.json"


def _empty() -> dict:
    return {"next_id": 1, "entries": []}


def _valid(data) -> bool:
    """Is this parsed JSON the shape we wrote? Anything else counts as damaged."""

    def is_int(x):
        return isinstance(x, int) and not isinstance(x, bool)

    def valid_file(f):
        return isinstance(f, dict) and isinstance(f.get("path"), str) \
            and isinstance(f.get("from"), str)

    def valid_entry(e):
        return (isinstance(e, dict) and is_int(e.get("id")) and isinstance(e.get("time"), str)
                and isinstance(e.get("to"), str) and isinstance(e.get("files"), list)
                and all(valid_file(f) for f in e["files"]))

    if not (isinstance(data, dict) and is_int(data.get("next_id"))
            and isinstance(data.get("entries"), list)
            and all(valid_entry(e) for e in data["entries"])):
        return False
    # next_id must be above every existing id, or ids could be handed out twice.
    return all(e["id"] < data["next_id"] for e in data["entries"])


def load() -> dict:
    """Read the cache. A missing or damaged file is an empty history (R2.7)."""
    try:
        data = json.loads(cache_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):  # ValueError covers bad JSON and bad UTF-8
        return _empty()
    return data if _valid(data) else _empty()


def save(data: dict) -> None:
    """Write the cache. Raises OSError if that is not possible."""
    path = cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(path, json.dumps(data, indent=2).encode("utf-8"))


def record(to: str, changed: list[tuple[Path, str]]) -> dict | None:
    """Add one entry for a convert run (R2.1) and return it.

    `changed` is a list of (path, original style) for the files that really
    changed. Returns None, and writes nothing, if the list is empty.
    May raise OSError from save().
    """
    if not changed:
        return None
    data = load()
    entry = {
        "id": data["next_id"],
        "time": datetime.now(timezone.utc).strftime(TIME_FORMAT),
        "to": to,
        "files": [{"path": str(path.resolve()), "from": style} for path, style in changed],
    }
    data["entries"].append(entry)
    data["entries"] = data["entries"][-MAX_ENTRIES:]  # R2.3: keep the newest 50
    data["next_id"] += 1
    save(data)
    return entry


def remove(entry_id: int) -> None:
    """Delete one entry from the cache (used after a revert). May raise OSError."""
    data = load()
    data["entries"] = [e for e in data["entries"] if e["id"] != entry_id]
    save(data)
