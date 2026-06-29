"""Small JSONL helpers shared by the learning core and adapters."""

from __future__ import annotations

import json
from pathlib import Path


def append_jsonl(path: Path, entry: dict) -> None:
    """Append one JSON object as a line, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_jsonl(path: Path, *, skip_bad: bool = True) -> list[dict]:
    """Read JSONL objects from ``path``.

    Missing files return ``[]``. When ``skip_bad`` is true, blank, malformed,
    and non-object lines are ignored so one corrupt history entry does not
    invalidate a whole learning track.
    """
    if not path.exists():
        return []
    rows: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            if skip_bad:
                continue
            raise
        if isinstance(obj, dict):
            rows.append(obj)
        elif not skip_bad:
            raise ValueError("JSONL line is not an object")
    return rows
