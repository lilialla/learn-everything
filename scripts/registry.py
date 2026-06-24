#!/usr/bin/env python3
"""Track / registry IO layer for the learn-everything learning OS.

This is the ONLY module that touches per-track files. The `learn` skill
shells out to the subcommands defined here.

Source of truth: per-track tracks/<id>/TRACK.md (YAML frontmatter + Log table).
registry.json at repo root is a REBUILDABLE cache, never the sole source.

Stdlib only: argparse, json, datetime, pathlib, re, math (math unused but
allowed). No third-party deps, no pyyaml.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Repo root = parent of the scripts/ dir that holds this file.
REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent


def repo_root() -> Path:
    """Return the repo root. Indirection lets tests monkeypatch easily."""
    return REPO_ROOT


# ---------------------------------------------------------------------------
# Tunable constants (orchestration). Surfaced here so they are not magic numbers
# scattered through the code; the daily planner and status board read them.
# ---------------------------------------------------------------------------

STALE_THRESHOLD_DAYS = 7  # a track idle longer than this is "stale"
LEECH_LAPSES = 3  # a card that has lapsed this many times is a "leech" — re-teach, don't re-quiz
URGENT_DAYS = 3  # a deadline within this many days is force-scheduled
SEC_PER_CARD = 40  # review-time estimate per due card
MAX_REVIEW_BLOCK_MIN = 25  # cap one track's review block so a backlog can't eat the day
MIN_PER_NEW_BLOCK = 30  # default minutes for a "learn something new" block
REANCHOR_MIN = 5  # quick "what was this track about" touch for a stale track
DEFAULT_BUDGET_MIN = 60  # default daily time budget when none given
MISSION_STUB_MARKER = "<!-- learn-everything:mission-stub -->"


def tracks_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / "tracks"


def registry_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / "registry.json"


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _warn(msg: str) -> None:
    print(f"warning: {msg}", file=sys.stderr)


def _today_str(today: str | None) -> str:
    """Resolve --today, defaulting to system date. Validates ISO format."""
    if today is None:
        return date.today().isoformat()
    # Validate; raises ValueError -> surfaced as clear error by callers.
    datetime.strptime(today, "%Y-%m-%d")
    return today


def _read_json(path: Path) -> dict:
    """Read a JSON file as UTF-8. Raises on missing/corrupt (callers decide)."""
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _atomic_write_text(path: Path, text: str) -> None:
    """Write text via a temp file + os.replace so a crash/sync mid-write can't
    truncate the target. Critical under Google Drive sync, where a torn
    review-state.json would otherwise trip the corrupt-state guard. The temp file
    is created in the SAME directory so os.replace is a true atomic rename.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _write_json(path: Path, data) -> None:
    _atomic_write_text(
        path, json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    )


# ---------------------------------------------------------------------------
# YAML frontmatter (minimal parser/emitter, no pyyaml)
# ---------------------------------------------------------------------------

FRONTMATTER_KEYS = [
    "id",
    "title",
    "mode",
    "pedagogy",
    "status",
    "created",
    "deadline",
    "last_active",
    "next_action",
]


def _scalar_to_yaml(value) -> str:
    """Emit a scalar for our simple `key: value` frontmatter."""
    if value is None:
        return "null"
    text = str(value)
    # Collapse newlines to spaces: a multi-line scalar would otherwise break the
    # single-line `key: value` frontmatter (and inject a bogus key-less line into
    # the `---` block). Mirrors the Log-cell behavior in append_log_row.
    text = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    if text == "":
        return '""'
    # Quote if it could be misread (contains a colon followed by space, leading
    # special char, or looks like a reserved word). Keep it conservative.
    needs_quote = (
        ": " in text
        or text[0] in "#&*!|>%@`\"'[]{},"
        or text.strip() != text
        or text in ("null", "true", "false")
    )
    if needs_quote:
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return text


def _scalar_from_yaml(raw: str):
    """Parse a scalar from our simple frontmatter. Returns str or None."""
    raw = raw.strip()
    if raw == "" or raw == "null" or raw == "~":
        return None
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
        inner = raw[1:-1]
        if raw[0] == '"':
            inner = inner.replace('\\"', '"').replace("\\\\", "\\")
        return inner
    return raw


def emit_frontmatter(meta: dict) -> str:
    """Build the `--- ... ---` YAML block from a metadata dict.

    Known keys are emitted first in FRONTMATTER_KEYS order; any extra keys the
    user added to TRACK.md are then appended (sorted) so they survive a round-trip
    through log/grade — TRACK.md is the source of truth, not just the schema.
    """
    lines = ["---"]
    for key in FRONTMATTER_KEYS:
        if key in meta:
            lines.append(f"{key}: {_scalar_to_yaml(meta[key])}")
    for key in sorted(k for k in meta if k not in FRONTMATTER_KEYS):
        lines.append(f"{key}: {_scalar_to_yaml(meta[key])}")
    lines.append("---")
    return "\n".join(lines)


def parse_frontmatter(text: str) -> dict:
    """Parse leading `--- ... ---` frontmatter into a dict. Empty dict if none."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    meta: dict = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, raw = line.partition(":")
        key = key.strip()
        if key:
            meta[key] = _scalar_from_yaml(raw)
    return meta


# ---------------------------------------------------------------------------
# TRACK.md read / write
# ---------------------------------------------------------------------------

def track_dir(track_id: str, root: Path | None = None) -> Path:
    return tracks_dir(root) / track_id


def track_md_path(track_id: str, root: Path | None = None) -> Path:
    return track_dir(track_id, root) / "TRACK.md"


def review_state_path(track_id: str, root: Path | None = None) -> Path:
    return track_dir(track_id, root) / "review-state.json"


def mission_path(track_id: str, root: Path | None = None) -> Path:
    return track_dir(track_id, root) / "MISSION.md"


def _mission_stub(title: str) -> str:
    """A MISSION.md scaffold. Carries a marker so the board can tell stub from real."""
    return (
        f"# Mission: {title}\n\n"
        f"{MISSION_STUB_MARKER}\n"
        "<!-- Fill this in with the host model on your first session. A vague mission\n"
        "     is worse than none — push for the concrete real-world why. -->\n\n"
        "## Why\n_TBD — the concrete real-world outcome you're chasing._\n\n"
        "## Success looks like\n- _TBD — a specific, observable thing you'll be able to do_\n\n"
        "## Constraints\n- _TBD — time / budget / preferences that bound the approach_\n\n"
        "## Out of scope\n- _TBD — adjacent things you are NOT chasing right now_\n"
    )


def mission_present(track_id: str, root: Path | None = None) -> bool:
    """True iff MISSION.md exists AND has been filled in (stub marker removed)."""
    path = mission_path(track_id, root)
    if not path.exists():
        return False
    try:
        return MISSION_STUB_MARKER not in path.read_text(encoding="utf-8")
    except OSError:
        return False


def _plan_md_skeleton(title: str) -> str:
    """A living map-of-content skeleton (not a dead stub), so the Obsidian
    split-screen has real structure to grow into: sessions + cards get linked here."""
    return (
        f"# {title} — Map of Content\n\n"
        "> The track's living map. As you learn, link each session and card here so the\n"
        "> whole track stays navigable (open this folder as an Obsidian vault).\n\n"
        "## Sessions\n"
        "<!-- one bullet per teaching/ingest session: date — topic — [[notes/<file>]] -->\n\n"
        "## Cards\n"
        "<!-- [[card-0001]] … grouped by theme as the deck grows -->\n"
    )


def _build_track_md(meta: dict, goal: str) -> str:
    """Compose a fresh TRACK.md body."""
    parts = [
        emit_frontmatter(meta),
        "",
        "## Goal",
        "",
        goal.strip() if goal else "_TBD_",
        "",
        "## Log",
        "",
        "| date | what happened | artifacts |",
        "| --- | --- | --- |",
        "",
    ]
    return "\n".join(parts)


def read_track(track_id: str, root: Path | None = None) -> dict:
    """Read TRACK.md frontmatter. Raises FileNotFoundError if missing."""
    path = track_md_path(track_id, root)
    text = path.read_text(encoding="utf-8")
    return parse_frontmatter(text)


def log_row_count(track_id: str, root: Path | None = None) -> int:
    """Count data rows in the '## Log' table (excludes header + separator)."""
    path = track_md_path(track_id, root)
    if not path.exists():
        return 0
    lines = path.read_text(encoding="utf-8").splitlines()
    in_log = False
    seen_sep = False
    n = 0
    for line in lines:
        s = line.strip()
        if s.lower() == "## log":
            in_log = True
            continue
        if not in_log:
            continue
        if s.startswith("## "):  # next section ends the Log block
            break
        if s.startswith("|") and set(s) <= set("|-: "):
            seen_sep = True
            continue
        if seen_sep and s.startswith("|"):
            n += 1
    return n


def log_dates(track_id: str, root: Path | None = None) -> set[str]:
    """The set of dates appearing in the '## Log' table's first column.

    Used to tell a real teaching/review Log row (dated today) apart from
    create_track's initial `last_active` stamp, which is not a session trace.
    """
    path = track_md_path(track_id, root)
    if not path.exists():
        return set()
    lines = path.read_text(encoding="utf-8").splitlines()
    in_log = False
    seen_sep = False
    out: set[str] = set()
    for line in lines:
        s = line.strip()
        if s.lower() == "## log":
            in_log = True
            continue
        if not in_log:
            continue
        if s.startswith("## "):
            break
        if s.startswith("|") and set(s) <= set("|-: "):
            seen_sep = True
            continue
        if seen_sep and s.startswith("|"):
            first = s.strip("|").split("|", 1)[0].strip()
            if first:
                out.add(first)
    return out


def _split_track_md(text: str) -> tuple[list[str], list[str]]:
    """Return (frontmatter_lines_with_fences, body_lines) split at 2nd '---'."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return [], lines
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return [], lines
    return lines[: end + 1], lines[end + 1 :]


def update_track_meta(track_id: str, updates: dict, root: Path | None = None) -> None:
    """Patch frontmatter keys in TRACK.md, preserving body (Goal/Log)."""
    path = track_md_path(track_id, root)
    text = path.read_text(encoding="utf-8")
    meta = parse_frontmatter(text)
    meta.update(updates)
    _, body_lines = _split_track_md(text)
    new_text = emit_frontmatter(meta) + "\n" + "\n".join(body_lines)
    if not new_text.endswith("\n"):
        new_text += "\n"
    _atomic_write_text(path, new_text)


def set_prefs(
    track_id: str,
    *,
    goal_weight: float | None = None,
    minutes_per_new_block: int | None = None,
    root: Path | None = None,
) -> dict:
    """Adjust a track's priority / time allocation (read by plan-day & status).

    ``goal_weight`` scales how strongly plan-day favors this track; ``minutes_per_new_block``
    sizes its "learn something new" block. Set either independently. This is the
    user-facing knob the engine already supported but never exposed.
    """
    if not track_md_path(track_id, root).exists():
        raise ValueError(f"unknown track '{track_id}'")
    updates: dict = {}
    if goal_weight is not None:
        if goal_weight <= 0:
            raise ValueError("goal_weight must be > 0")
        updates["goal_weight"] = goal_weight
    if minutes_per_new_block is not None:
        if minutes_per_new_block <= 0:
            raise ValueError("minutes_per_new_block must be > 0")
        updates["minutes_per_new_block"] = minutes_per_new_block
    if not updates:
        raise ValueError(
            "nothing to set — pass goal_weight and/or minutes_per_new_block"
        )
    update_track_meta(track_id, updates, root)
    rebuild_registry(root)
    # Frontmatter is stored as strings (consumers coerce via _num); report back the
    # numeric values that were actually set.
    return {"track": track_id, **updates}


def append_log_row(
    track_id: str,
    today: str,
    what: str,
    artifacts: str = "",
    root: Path | None = None,
) -> None:
    """Append a row to the '## Log' markdown table in TRACK.md."""
    path = track_md_path(track_id, root)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    def _cell(value: str) -> str:
        # Escape pipes so the table stays valid.
        return (value or "").replace("|", "\\|").replace("\n", " ").strip()

    row = f"| {_cell(today)} | {_cell(what)} | {_cell(artifacts)} |"

    # Find the Log table. Append after the last existing table row, or after
    # the header separator if no rows yet.
    log_idx = None
    for i, line in enumerate(lines):
        if line.strip().lower() == "## log":
            log_idx = i
            break
    if log_idx is None:
        # No Log section: create one at the end.
        if lines and lines[-1].strip():
            lines.append("")
        lines += [
            "## Log",
            "",
            "| date | what happened | artifacts |",
            "| --- | --- | --- |",
            row,
        ]
    else:
        # Find last contiguous table row at/after the separator.
        insert_at = len(lines)
        seen_separator = False
        for i in range(log_idx + 1, len(lines)):
            stripped = lines[i].strip()
            if stripped.startswith("|") and set(stripped) <= set("|-: "):
                seen_separator = True
                insert_at = i + 1
                continue
            if seen_separator and stripped.startswith("|"):
                insert_at = i + 1
            elif seen_separator and not stripped.startswith("|"):
                # End of table block.
                break
        lines.insert(insert_at, row)

    new_text = "\n".join(lines)
    if not new_text.endswith("\n"):
        new_text += "\n"
    _atomic_write_text(path, new_text)


# ---------------------------------------------------------------------------
# Review-state (FSRS sidecar)
# ---------------------------------------------------------------------------

def load_review_state(
    track_id: str, root: Path | None = None, on_corrupt: str = "lenient"
) -> dict:
    """Load review-state.json.

    `on_corrupt='lenient'` (read-only callers: due/status): missing/corrupt -> {}
    with a warning, treating cards as new — safe because nothing is written back.

    `on_corrupt='raise'` (write callers: grade/add-card): a corrupt file aborts the
    mutation instead of overwriting it, which would silently zero every OTHER card's
    FSRS state. The bad file is renamed to review-state.json.bad.<ts> so the operator
    can recover it, then a ValueError is raised.
    """
    path = review_state_path(track_id, root)
    if not path.exists():
        return {}
    try:
        data = _read_json(path)
        if not isinstance(data, dict):
            raise ValueError("review-state.json is not a JSON object")
        return data
    except (json.JSONDecodeError, ValueError, OSError) as exc:
        if on_corrupt == "raise":
            ts = datetime.now().strftime("%Y%m%dT%H%M%S")
            bad_path = path.with_name(f"{path.name}.bad.{ts}")
            try:
                path.rename(bad_path)
                _warn(
                    f"review-state.json for track '{track_id}' is corrupt ({exc}); "
                    f"moved to {bad_path.name} and aborting the write to avoid "
                    f"clobbering other cards' FSRS state"
                )
            except OSError as rename_exc:
                _warn(
                    f"review-state.json for track '{track_id}' is corrupt ({exc}) "
                    f"and could not be quarantined ({rename_exc})"
                )
            raise ValueError(
                f"review-state.json for track '{track_id}' is corrupt; refusing "
                f"to overwrite it"
            ) from exc
        _warn(
            f"review-state.json for track '{track_id}' is missing/corrupt "
            f"({exc}); treating its cards as new"
        )
        return {}


def save_review_state(track_id: str, state: dict, root: Path | None = None) -> None:
    _write_json(review_state_path(track_id, root), state)


def review_log_path(track_id: str, root: Path | None = None) -> Path:
    return track_dir(track_id, root) / "review-log.jsonl"


def append_review_log(track_id: str, entry: dict, root: Path | None = None) -> None:
    """Append one grading event to review-log.jsonl (append-only history).

    This is the data the future personalized-weights optimizer + leech detection
    read. It is best-effort: a logging failure must NEVER break grading, so we
    warn and continue rather than raise.
    """
    try:
        path = review_log_path(track_id, root)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as exc:  # pragma: no cover - defensive
        _warn(f"could not append review-log for '{track_id}' ({exc}); continuing")


def _seed_new_card_state(today: str) -> dict:
    """Initial FSRS sidecar entry for a brand-new card."""
    return {
        "stability": None,
        "difficulty": None,
        "due": today,
        "reps": 0,
        "lapses": 0,
        "last_review": None,
        "state": "new",
    }


# ---------------------------------------------------------------------------
# Card files
# ---------------------------------------------------------------------------

CARD_ID_RE = re.compile(r"^card-(\d+)\.md$")


def cards_dir(track_id: str, root: Path | None = None) -> Path:
    return track_dir(track_id, root) / "cards"


def list_card_ids(track_id: str, root: Path | None = None) -> list[str]:
    """Return sorted card ids (e.g. ['card-0001', ...]) for a track."""
    cdir = cards_dir(track_id, root)
    if not cdir.exists():
        return []
    ids = []
    for entry in cdir.iterdir():
        m = CARD_ID_RE.match(entry.name)
        if m:
            ids.append((int(m.group(1)), entry.stem))
    ids.sort()
    return [stem for _, stem in ids]


def next_card_id(track_id: str, root: Path | None = None) -> str:
    """Allocator = max-existing + 1, zero-padded to 4 digits."""
    cdir = cards_dir(track_id, root)
    max_n = 0
    if cdir.exists():
        for entry in cdir.iterdir():
            m = CARD_ID_RE.match(entry.name)
            if m:
                max_n = max(max_n, int(m.group(1)))
    return f"card-{max_n + 1:04d}"


def _build_card_md(
    card_id: str,
    question: str,
    answer: str,
    tags: list[str],
    track_id: str,
    source: str = "",
) -> str:
    """Card body, compatible with the Obsidian spaced-repetition plugin.

    Uses that plugin's multi-line `?` separator plus a `#flashcards/<track>`
    subdeck tag, so cards review natively inside Obsidian while staying clean,
    human-readable markdown. FSRS scheduling state lives in review-state.json,
    never in the card file, so cards can be edited/exported freely.

    `source` (optional) records provenance — the note/file/url (and page/anchor)
    this card was distilled from — so a learner can always trace a card back to
    where the fact came from. Emitted as a frontmatter line only when present.
    """
    tag_line = "[" + ", ".join(tags) + "]"
    source_line = f"source: {_scalar_to_yaml(source.strip())}\n" if source.strip() else ""
    return (
        "---\n"
        f"id: {card_id}\n"
        f"tags: {tag_line}\n"
        f"{source_line}"
        "---\n"
        f"#flashcards/{track_id}\n"
        "\n"
        f"{question.strip()}\n"
        "?\n"
        f"{answer.strip()}\n"
    )


def read_card_question(track_id: str, card_id: str, root: Path | None = None) -> str:
    """Extract the question text from a card file; '' if not found.

    Supports every Obsidian spaced-repetition card shape so the answer is never
    leaked in the `due` listing:
    - multi-line: question lines before a lone `?`/`??` separator (our own format)
    - inline: `Question::Answer` / `Question:::Answer` -> text before `::`
    - cloze:   a line with `==answer==` -> the line with cloze blanked to `[...]`
    - legacy:  `**Q:**` prefix
    """
    path = cards_dir(track_id, root) / f"{card_id}.md"
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    _, body_lines = _split_track_md(text)  # drop frontmatter
    q_lines: list[str] = []
    for line in body_lines:
        stripped = line.strip()
        if stripped in ("?", "??"):
            if q_lines:
                return " ".join(q_lines).strip()
            break
        if not stripped or stripped.startswith("#"):
            continue  # skip blank lines and the #flashcards tag
        q_lines.append(stripped)

    # No `?` separator found: try hand-authored inline / cloze forms on the
    # first real content line (never return the answer side).
    first = q_lines[0] if q_lines else ""
    if "::" in first:
        return first.split("::", 1)[0].strip()
    if "==" in first:
        return re.sub(r"==(.+?)==", "[...]", first).strip()
    # Legacy fallback for old `**Q:**` cards.
    m = re.search(r"\*\*Q:\*\*\s*(.+)", text)
    return m.group(1).strip() if m else " ".join(q_lines).strip()


# ---------------------------------------------------------------------------
# fsrs wiring
# ---------------------------------------------------------------------------
#
# We call fsrs through its CLI (`fsrs.py schedule --state ... --grade ... --now`)
# rather than importing its Python function. The CLI is the contract-stable
# interface (`--now YYYY-MM-DD` string in, JSON card-state out), so the registry
# layer stays decoupled from fsrs's internal function signature. Non-grading
# subcommands never touch fsrs, so they work even if fsrs.py is absent.


def _fsrs_cli_scheduler(state, grade: int, now: str, weights_path: str | None = None) -> dict:
    """Run scripts/fsrs.py's `schedule` subcommand and return the new state."""
    import subprocess

    fsrs_path = SCRIPTS_DIR / "fsrs.py"
    if not fsrs_path.exists():
        raise ImportError(f"fsrs scheduler not found at {fsrs_path}")
    state_arg = "-" if not state else json.dumps(state, ensure_ascii=False)
    cmd = [
        sys.executable, str(fsrs_path), "schedule",
        "--state", state_arg, "--grade", str(grade), "--now", now,
    ]
    if weights_path:  # personalized weights from adapters/fsrs_optimize, if present
        cmd += ["--weights", weights_path]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise ValueError(
            f"fsrs schedule failed (exit {proc.returncode}): "
            f"{proc.stderr.strip() or proc.stdout.strip()}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"fsrs schedule returned non-JSON output: {exc}")


def _track_weights_path(track_id: str, root: Path | None = None) -> str | None:
    """Per-track personalized FSRS weights, if the optimizer adapter wrote one."""
    p = track_dir(track_id, root) / "fsrs-weights.json"
    return str(p) if p.exists() else None


def _default_scheduler(track_id: str | None = None, root: Path | None = None):
    """Default scheduler (CLI-backed); auto-uses per-track personalized weights if present."""
    wp = _track_weights_path(track_id, root) if track_id else None
    return lambda state, grade, now: _fsrs_cli_scheduler(state, grade, now, weights_path=wp)


# ---------------------------------------------------------------------------
# Core operations (importable; CLI wraps these)
# ---------------------------------------------------------------------------

def create_track(
    track_id: str,
    title: str,
    mode: str,
    pedagogy: str,
    deadline: str | None = None,
    goal: str = "",
    today: str | None = None,
    root: Path | None = None,
) -> Path:
    """Scaffold a new track. Errors (ValueError) if the id already exists."""
    tdir = track_dir(track_id, root)
    if tdir.exists():
        raise ValueError(f"track '{track_id}' already exists at {tdir}")

    today = _today_str(today)
    meta = {
        "id": track_id,
        "title": title,
        "mode": mode,
        "pedagogy": pedagogy,
        "status": "active",
        "created": today,
        "deadline": deadline,  # may be None
        "last_active": today,
        "next_action": None,
    }

    (tdir / "cards").mkdir(parents=True, exist_ok=True)
    (tdir / "notes").mkdir(parents=True, exist_ok=True)
    _atomic_write_text(track_md_path(track_id, root), _build_track_md(meta, goal))
    _atomic_write_text(tdir / "plan.md", _plan_md_skeleton(title))
    # Scaffold a MISSION.md stub so the "ground every track in a why" discipline
    # (methods/learning-science.md) can't be silently skipped — the board flags it
    # as not-yet-filled until the stub marker is removed.
    _atomic_write_text(mission_path(track_id, root), _mission_stub(title))
    save_review_state(track_id, {}, root)

    rebuild_registry(root)
    return tdir


def _track_record(track_id: str, root: Path | None = None) -> dict | None:
    """Build a registry record from one track's TRACK.md. None if unreadable."""
    try:
        meta = read_track(track_id, root)
    except (FileNotFoundError, OSError) as exc:
        _warn(f"cannot read TRACK.md for '{track_id}' ({exc}); skipping")
        return None
    if not meta.get("id"):
        meta["id"] = track_id
    return {
        "id": meta.get("id", track_id),
        "title": meta.get("title"),
        "mode": meta.get("mode"),
        "pedagogy": meta.get("pedagogy"),
        "status": meta.get("status"),
        "created": meta.get("created"),
        "deadline": meta.get("deadline"),
        "last_active": meta.get("last_active"),
        "next_action": meta.get("next_action"),
        "goal_weight": meta.get("goal_weight"),
        "minutes_per_new_block": meta.get("minutes_per_new_block"),
        "cards_total": len(list_card_ids(track_id, root)),
    }


def rebuild_registry(root: Path | None = None) -> dict:
    """Scan tracks/*/TRACK.md, write+return registry.json contents."""
    tdir = tracks_dir(root)
    records = []
    if tdir.exists():
        for entry in sorted(tdir.iterdir()):
            if not entry.is_dir():
                continue
            if not (entry / "TRACK.md").exists():
                continue
            rec = _track_record(entry.name, root)
            if rec is not None:
                records.append(rec)
    registry = {"tracks": records}
    _write_json(registry_path(root), registry)
    return registry


def load_registry(root: Path | None = None) -> dict:
    """Load registry.json; rebuild from TRACK.md if missing/corrupt."""
    path = registry_path(root)
    if path.exists():
        try:
            data = _read_json(path)
            if isinstance(data, dict) and "tracks" in data:
                return data
            raise ValueError("registry.json missing 'tracks' key")
        except (json.JSONDecodeError, ValueError, OSError) as exc:
            _warn(f"registry.json missing/corrupt ({exc}); rebuilding from TRACK.md")
    return rebuild_registry(root)


def _days_between(today: str, other: str | None) -> int | None:
    if not other:
        return None
    try:
        d0 = datetime.strptime(today, "%Y-%m-%d").date()
        d1 = datetime.strptime(other, "%Y-%m-%d").date()
    except ValueError:
        return None
    return (d1 - d0).days


def _cards_due_today(track_id: str, today: str, root: Path | None = None) -> int:
    state = load_review_state(track_id, root)
    count = 0
    for card_id in list_card_ids(track_id, root):
        entry = state.get(card_id)
        if not isinstance(entry, dict):
            # Unseeded or malformed entry behaves as new -> due now.
            count += 1
            continue
        due = entry.get("due")
        if due is None or _due_le(due, today):
            count += 1
    return count


def _count_leeches(track_id: str, root: Path | None = None) -> int:
    state = load_review_state(track_id, root)
    n = 0
    for card_id in list_card_ids(track_id, root):
        entry = state.get(card_id)
        if isinstance(entry, dict) and (entry.get("lapses") or 0) >= LEECH_LAPSES:
            n += 1
    return n


def leeches(track_id: str, root: Path | None = None) -> dict:
    """Cards that keep failing (lapses >= LEECH_LAPSES) — re-teach, don't re-quiz.

    Returns the offending cards with their lapse/rep counts and question text so
    the skill can offer a fresh explanation + a clearer replacement card.
    """
    if not track_md_path(track_id, root).exists():
        raise ValueError(f"unknown track '{track_id}'")
    state = load_review_state(track_id, root)
    out = []
    for card_id in list_card_ids(track_id, root):
        entry = state.get(card_id)
        if not isinstance(entry, dict):
            continue
        if (entry.get("lapses") or 0) >= LEECH_LAPSES:
            out.append({
                "card_id": card_id,
                "lapses": entry.get("lapses"),
                "reps": entry.get("reps"),
                "question": read_card_question(track_id, card_id, root),
            })
    out.sort(key=lambda c: (-(c["lapses"] or 0), c["card_id"]))
    return {"track": track_id, "count": len(out), "leeches": out}


def nudge(today: str | None = None, root: Path | None = None) -> str:
    """ONE plain human line for a daily note / cron / scheduled agent.

    No JSON — this is what a learner sees outside the app to know it's time to
    review. Surfaces the due count, the leech count, and the urgent-deadline
    count so re-engagement doesn't depend on the learner remembering to ask.
    """
    board = status_board(today, root)
    due = board["due_total"]
    n_tracks = board["tracks_with_due"]
    leech_total = sum(t.get("leeches", 0) for t in board["tracks"])
    # Match status_board's sort: a deadline within URGENT_DAYS *or already past*
    # is urgent. (A stray `0 <=` lower bound used to hide overdue items from the
    # very daily-note/cron surface meant to re-engage the learner.)
    urgent = sum(
        1 for t in board["tracks"]
        if t["days_to_deadline"] is not None and t["days_to_deadline"] < URGENT_DAYS
    )
    if due == 0 and urgent == 0:
        return "learn-everything: nothing due today — a good day to learn something new."
    parts = []
    if due:
        s = "card" if due == 1 else "cards"
        t = "subject" if n_tracks == 1 else "subjects"
        parts.append(f"{due} {s} due across {n_tracks} {t}")
    if urgent:
        d_s = "deadline" if urgent == 1 else "deadlines"
        parts.append(f"{urgent} with a {d_s} due soon/overdue")
    if leech_total:
        parts.append(f"{leech_total} to re-teach")
    return "learn-everything: " + "; ".join(parts) + " — open it and ask “what should I do?”"


def _due_le(due: str, today: str) -> bool:
    """True if due <= today (string ISO dates)."""
    try:
        return (
            datetime.strptime(due, "%Y-%m-%d").date()
            <= datetime.strptime(today, "%Y-%m-%d").date()
        )
    except ValueError:
        # Unparseable due -> treat as due now to be safe.
        return True


def status_board(today: str | None = None, root: Path | None = None) -> dict:
    """Rebuild then return a status board with deadline/due/stale per track."""
    today = _today_str(today)
    registry = rebuild_registry(root)
    board = []
    for rec in registry["tracks"]:
        track_id = rec["id"]
        days_to_deadline = _days_between(today, rec.get("deadline"))
        last_active = rec.get("last_active")
        stale_days = _days_between(last_active, today) if last_active else None
        stale = bool(stale_days is not None and stale_days > STALE_THRESHOLD_DAYS)
        cards_total = rec.get("cards_total") or 0
        # "Taught but retaining nothing": an active track that has had activity
        # beyond its creation day yet has produced zero cards — the FSRS safety
        # net is never engaged. Surfaced so STATUS can nudge distilling cards.
        taught_since_created = bool(
            (_days_between(rec.get("created"), last_active) or 0) > 0
        )
        needs_cards = bool(
            rec.get("status") == "active" and cards_total == 0 and taught_since_created
        )
        # A track that's been taught but has no way to resume (no next step, no log):
        # exactly the failure where RESUME returns a blank pointer.
        resume_pointer_missing = bool(
            taught_since_created
            and not rec.get("next_action")
            and log_row_count(track_id, root) == 0
        )
        board.append(
            {
                "id": track_id,
                "title": rec.get("title"),
                "mode": rec.get("mode"),
                "pedagogy": rec.get("pedagogy"),
                "status": rec.get("status"),
                "days_to_deadline": days_to_deadline,
                "cards_due_today": _cards_due_today(track_id, today, root),
                "cards_total": cards_total,
                "leeches": _count_leeches(track_id, root),
                "last_active": last_active,
                "stale_days": stale_days,
                "stale": stale,
                "needs_cards": needs_cards,
                "resume_pointer_missing": resume_pointer_missing,
                "mission_present": mission_present(track_id, root),
                "next_action": rec.get("next_action"),
                "goal_weight": rec.get("goal_weight"),
                "minutes_per_new_block": rec.get("minutes_per_new_block"),
            }
        )
    # Deterministic "do this next" ordering (bridge until plan-day ships):
    # 1) deadline within 3 days, 2) most cards due today, 3) stale before fresh,
    # 4) id as a stable tiebreaker.
    board.sort(
        key=lambda t: (
            0
            if (t["days_to_deadline"] is not None and t["days_to_deadline"] < 3)
            else 1,
            -(t["cards_due_today"] or 0),
            0 if t["stale"] else 1,
            t["id"],
        )
    )
    due_total = sum((t["cards_due_today"] or 0) for t in board)
    tracks_with_due = sum(1 for t in board if (t["cards_due_today"] or 0) > 0)
    leech_total = sum((t.get("leeches") or 0) for t in board)
    return {
        "today": today,
        "due_total": due_total,
        "tracks_with_due": tracks_with_due,
        "leech_total": leech_total,
        "tracks": board,
    }


def _num(value, default: float) -> float:
    """Best-effort numeric coercion of an optional frontmatter value."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _interleave_ties(blocks: list[dict]) -> list[dict]:
    """De-cluster blocks of EQUAL score so one track doesn't stack back-to-back.

    Only reorders within exact-score runs (never promotes a lower score above a
    higher one), and greedily avoids repeating the previously emitted track.
    Deterministic for a fixed input.
    """
    out: list[dict] = []
    i, n = 0, len(blocks)
    while i < n:
        j = i
        while j < n and blocks[j]["score"] == blocks[i]["score"]:
            j += 1
        remaining = blocks[i:j]
        while remaining:
            prev = out[-1]["track"] if out else None
            pick = next((b for b in remaining if b["track"] != prev), remaining[0])
            out.append(pick)
            remaining.remove(pick)
        i = j
    return out


def plan_day(
    today: str | None = None,
    minutes: int | None = None,
    energy: str = "normal",
    root: Path | None = None,
) -> dict:
    """Deterministic, time-boxed daily plan across all active tracks.

    The ENGINE ranks + time-boxes (reproducible, testable); the host model only
    narrates the given order. Read-only — writes nothing, like status/due.
    """
    import math

    today = _today_str(today)
    budget = int(minutes) if minutes is not None else DEFAULT_BUDGET_MIN
    energy = energy if energy in ("low", "normal", "high") else "normal"

    board = status_board(today, root)["tracks"]
    blocks: list[dict] = []
    for t in board:
        if t.get("status") != "active":
            continue
        tid = t["id"]
        d2d = t.get("days_to_deadline")
        gw = _num(t.get("goal_weight"), 1.0)
        if d2d is None:
            deadline_score = 0.0
        elif d2d < 0:
            deadline_score = 300.0  # overdue
        elif d2d <= 14:
            deadline_score = (15 - d2d) * 10.0
        else:
            deadline_score = 0.0
        urgent = d2d is not None and d2d <= URGENT_DAYS
        deadline_reason = (
            ["overdue"] if (d2d is not None and d2d < 0)
            else (["deadline"] if deadline_score > 0 else [])
        )
        chose_review_or_new = False

        due = t.get("cards_due_today") or 0
        if due > 0:
            est = min(MAX_REVIEW_BLOCK_MIN, max(1, math.ceil(due * SEC_PER_CARD / 60)))
            score = (deadline_score + due * 3 + 5) * gw
            blocks.append({
                "track": tid, "title": t.get("title"), "kind": "review",
                "action": f"review --track {tid}", "est_min": est, "due_count": due,
                "score": round(score, 3), "urgent": urgent, "d2d": d2d,
                "reason_codes": deadline_reason + ["due_cards"],
            })
            chose_review_or_new = True

        na = t.get("next_action")
        if na:
            mpn = int(_num(t.get("minutes_per_new_block"), MIN_PER_NEW_BLOCK))
            if energy == "low":
                mpn = max(5, int(mpn * 0.6))
            new_score = (deadline_score + 4) * gw
            if energy == "low":
                new_score *= 0.5  # demote learning-new when low energy
            blocks.append({
                "track": tid, "title": t.get("title"), "kind": "new",
                "action": f"resume --track {tid}", "est_min": mpn, "due_count": 0,
                "score": round(new_score, 3), "urgent": urgent, "d2d": d2d,
                "next_action": na, "reason_codes": deadline_reason + ["next_action"],
            })
            chose_review_or_new = True

        if t.get("stale") and not chose_review_or_new:
            sd = t.get("stale_days") or 0
            score = (min(sd, 60) + 1) * gw
            blocks.append({
                "track": tid, "title": t.get("title"), "kind": "re-anchor",
                "action": f"resume --track {tid}", "est_min": REANCHOR_MIN,
                "due_count": 0, "score": round(score, 3), "urgent": urgent, "d2d": d2d,
                "stale_days": sd, "reason_codes": ["stale"],
            })

    blocks.sort(
        key=lambda b: (-b["score"], b["d2d"] if b["d2d"] is not None else 10**9, b["track"], b["kind"])
    )
    blocks = _interleave_ties(blocks)

    scheduled: list[dict] = []
    deferred: list[dict] = []
    total = 0
    extra_new_used = False
    for b in blocks:
        fits = total + b["est_min"] <= budget
        force = bool(b["urgent"])
        bonus = energy == "high" and b["kind"] == "new" and not extra_new_used
        if fits or force or bonus:
            if not fits and force:
                b = {**b, "reason_codes": b["reason_codes"] + ["budget_exceeded_for_deadline"]}
            elif not fits and bonus:
                b = {**b, "reason_codes": b["reason_codes"] + ["energy_high_bonus"]}
                extra_new_used = True
            scheduled.append(b)
            total += b["est_min"]
        else:
            deferred.append({**b, "reason_codes": b["reason_codes"] + ["over_budget"]})

    tracks_touched = sorted({b["track"] for b in scheduled})
    return {
        "today": today,
        "budget_min": budget,
        "energy": energy,
        "scheduled": scheduled,
        "deferred": deferred,
        "summary": {
            "total_min": total,
            "budget_min": budget,
            "tracks_touched": len(tracks_touched),
            "blocks": len(scheduled),
        },
    }


def add_card(
    track_id: str,
    question: str,
    answer: str,
    tags: list[str] | None = None,
    today: str | None = None,
    root: Path | None = None,
    source: str = "",
) -> str:
    """Allocate id, write card file, seed review-state. Returns new card id.

    `source` records where the card came from (note path / url / page) for
    traceability; optional.
    """
    if not track_md_path(track_id, root).exists():
        raise ValueError(f"unknown track '{track_id}'")
    today = _today_str(today)
    tags = tags or []
    card_id = next_card_id(track_id, root)
    cards_dir(track_id, root).mkdir(parents=True, exist_ok=True)
    _atomic_write_text(
        cards_dir(track_id, root) / f"{card_id}.md",
        _build_card_md(card_id, question, answer, tags, track_id, source),
    )
    state = load_review_state(track_id, root, on_corrupt="raise")
    state[card_id] = _seed_new_card_state(today)
    save_review_state(track_id, state, root)
    return card_id


def add_cards(
    track_id: str,
    cards: list[dict],
    today: str | None = None,
    root: Path | None = None,
) -> list[str]:
    """Add several cards in ONE batch — the human-approved set from an ingest.

    Loads/saves review-state.json ONCE (not once-per-card) and is all-or-nothing:
    on any failure, the card files written this call are removed so a partial set
    never leaks. Each card is a dict {question, answer, tags?:list[str]}.
    """
    if not track_md_path(track_id, root).exists():
        raise ValueError(f"unknown track '{track_id}'")
    if not isinstance(cards, list) or not cards:
        raise ValueError("add_cards needs a non-empty list of cards")
    today = _today_str(today)

    state = load_review_state(track_id, root, on_corrupt="raise")
    cdir = cards_dir(track_id, root)
    cdir.mkdir(parents=True, exist_ok=True)

    # Allocate all ids up front from the current max so the batch is contiguous.
    start = 0
    for cid in list_card_ids(track_id, root):
        m = CARD_ID_RE.match(f"{cid}.md")
        if m:
            start = max(start, int(m.group(1)))

    written: list[Path] = []
    new_ids: list[str] = []
    try:
        for i, card in enumerate(cards, start=1):
            q = (card.get("question") or "").strip()
            a = (card.get("answer") or "").strip()
            if not q or not a:
                raise ValueError(f"card #{i} is missing question or answer")
            tags = card.get("tags") or []
            source = (card.get("source") or "").strip()
            card_id = f"card-{start + i:04d}"
            path = cdir / f"{card_id}.md"
            _atomic_write_text(
                path, _build_card_md(card_id, q, a, list(tags), track_id, source)
            )
            written.append(path)
            state[card_id] = _seed_new_card_state(today)
            new_ids.append(card_id)
        save_review_state(track_id, state, root)  # single write
    except Exception:
        for p in written:  # rollback partial card files
            try:
                p.unlink()
            except OSError:
                pass
        raise

    rebuild_registry(root)
    return new_ids


def due_cards(
    track: str = "all",
    today: str | None = None,
    root: Path | None = None,
) -> list[dict]:
    """Collect due cards (due <= today) across tracks (or one)."""
    today = _today_str(today)
    if track and track != "all":
        track_ids = [track]
        if not track_md_path(track, root).exists():
            raise ValueError(f"unknown track '{track}'")
    else:
        track_ids = [rec["id"] for rec in rebuild_registry(root)["tracks"]]

    result = []
    for track_id in track_ids:
        state = load_review_state(track_id, root)
        for card_id in list_card_ids(track_id, root):
            entry = state.get(card_id)
            # unseeded or malformed -> due now
            due = entry.get("due") if isinstance(entry, dict) else today
            if due is None or _due_le(due, today):
                e = entry if isinstance(entry, dict) else {}
                result.append(
                    {
                        "track": track_id,
                        "card": card_id,
                        "question": read_card_question(track_id, card_id, root),
                        "due": due if due is not None else today,
                        # lapses/reps let the review loop spot leeches (a card that
                        # keeps failing) and switch pedagogy — see active-recall.md.
                        "lapses": e.get("lapses", 0),
                        "reps": e.get("reps", 0),
                    }
                )
    return result


def grade_card(
    track_id: str,
    card_id: str,
    grade: int,
    today: str | None = None,
    root: Path | None = None,
    scheduler=None,
) -> str:
    """Grade a card via fsrs.schedule, persist new state, return new due date.

    `scheduler` lets tests inject a fake schedule(state, grade, now) -> dict.
    """
    if grade not in (1, 2, 3, 4):
        raise ValueError(f"grade must be 1..4, got {grade!r}")
    if not track_md_path(track_id, root).exists():
        raise ValueError(f"unknown track '{track_id}'")
    if not (cards_dir(track_id, root) / f"{card_id}.md").exists():
        raise ValueError(f"unknown card '{card_id}' in track '{track_id}'")

    today = _today_str(today)
    state = load_review_state(track_id, root, on_corrupt="raise")
    prior = state.get(card_id)
    if not isinstance(prior, dict):
        prior = None  # malformed entry -> treat as new
    # A brand-new (or unseeded) card has no prior FSRS state.
    prior_for_fsrs = None if (prior is None or prior.get("state") == "new") else prior

    sched = scheduler or _default_scheduler(track_id, root)
    new_state = sched(prior_for_fsrs, grade, today)
    if not isinstance(new_state, dict) or "due" not in new_state:
        raise ValueError("scheduler returned an invalid card state")

    state[card_id] = new_state
    save_review_state(track_id, state, root)

    # Append-only grading history: feeds leech detection + future weight tuning.
    append_review_log(
        track_id,
        {
            "date": today,
            "card": card_id,
            "grade": grade,
            "due": new_state.get("due"),
            "reps": new_state.get("reps"),
            "lapses": new_state.get("lapses"),
            "state": new_state.get("state"),
        },
        root,
    )

    update_track_meta(track_id, {"last_active": today}, root)
    rebuild_registry(root)
    return new_state["due"]


NO_CARDS_MARKER = "no-cards-reason:"


def log_entry(
    track_id: str,
    what: str,
    next_action: str | None = None,
    artifacts: str = "",
    today: str | None = None,
    no_cards_reason: str | None = None,
    root: Path | None = None,
) -> None:
    """Append a Log row, bump last_active/next_action, rebuild registry.

    `no_cards_reason` records the allowed "taught but made no card (yet)" state so
    session-check can tell a deliberate no-card session from a silently-dropped one.
    """
    if not track_md_path(track_id, root).exists():
        raise ValueError(f"unknown track '{track_id}'")
    today = _today_str(today)
    if no_cards_reason:
        what = f"{what}  [{NO_CARDS_MARKER} {no_cards_reason.strip()}]"
    append_log_row(track_id, today, what, artifacts, root)
    updates = {"last_active": today}
    if next_action is not None:
        updates["next_action"] = next_action
    update_track_meta(track_id, updates, root)
    rebuild_registry(root)


def session_check(track_id: str, root: Path | None = None) -> dict:
    """Was a retention trace left? A track must have ≥1 card OR a logged reason why not.

    This makes "teach-first" measurable without silent gaps: a teaching session may
    legitimately end with no card, but only if it says why (`log --no-cards-reason`).
    Read-only over existing artifacts (card files + TRACK.md Log).
    """
    if not track_md_path(track_id, root).exists():
        raise ValueError(f"unknown track '{track_id}'")
    cards = len(list_card_ids(track_id, root))
    if cards > 0:
        return {"ok": True, "cards_total": cards, "reason": f"{cards} card(s) on this track"}
    text = track_md_path(track_id, root).read_text(encoding="utf-8")
    if NO_CARDS_MARKER in text:
        return {
            "ok": True,
            "cards_total": 0,
            "reason": "no cards yet, but a reason was logged",
        }
    return {
        "ok": False,
        "cards_total": 0,
        "reason": (
            "this track has 0 cards and no logged reason — distill at least one card "
            "from what was taught, or run `log --no-cards-reason \"<why>\"`"
        ),
    }


# A CONTEXT.md digest should stay a SMALL, bounded reconstruction of the learner
# (not an ever-growing log). Over this many chars, session-close warns the skill
# to summarize old sticking points instead of appending. ~6000 chars ≈ 1.5k tokens.
CONTEXT_MAX_CHARS = 6000


def context_md_path(track_id: str, root: Path | None = None) -> Path:
    """Per-track memory digest the skill reads first to reconstruct context."""
    return track_dir(track_id, root) / "CONTEXT.md"


def context_check(
    track_id: str, today: str | None = None, root: Path | None = None
) -> dict:
    """Is the per-track CONTEXT.md present, fresh (updated today), and bounded?

    The skill is expected to write a `last_updated: YYYY-MM-DD` line at the top of
    CONTEXT.md each session. This reads that marker (no write) and flags an
    over-budget digest so context never silently grows unbounded.
    """
    today = _today_str(today)
    path = context_md_path(track_id, root)
    if not path.exists():
        return {
            "exists": False, "fresh": False, "last_updated": None,
            "size_chars": 0, "over_budget": False,
        }
    text = path.read_text(encoding="utf-8")
    last_updated = None
    for line in text.splitlines()[:15]:
        s = line.strip().lstrip("-* ").lower()
        if s.startswith("last_updated:") or s.startswith("last updated:"):
            last_updated = line.split(":", 1)[1].strip()
            break
    size = len(text)
    return {
        "exists": True,
        "fresh": last_updated == today,
        "last_updated": last_updated,
        "size_chars": size,
        "over_budget": size > CONTEXT_MAX_CHARS,
    }


def session_close_check(
    track_id: str,
    taught: bool = True,
    today: str | None = None,
    root: Path | None = None,
) -> dict:
    """Strict, non-skippable session-close gate (the root-cause fix for memory).

    A teaching session is only "closed" if it left a durable, resumable trace:
      1. a card OR a logged no-cards reason  (existing `session_check`)
      2. a Log row dated today               (last_active == today)
      3. a `next_action` pointer set         (so RESUME isn't a blank)
      4. a CONTEXT.md updated today          (the memory digest is current)
    Plus a non-blocking warning if CONTEXT.md is over the size budget.

    Pass `taught=False` for a pure review/admin session: only requirement (3) the
    next_action and a Log row are enforced (no new card is expected from review).
    Read-only over existing artifacts; returns what's missing so the skill can fix
    it before declaring the session done.
    """
    if not track_md_path(track_id, root).exists():
        raise ValueError(f"unknown track '{track_id}'")
    today = _today_str(today)
    meta = read_track(track_id, root)
    ctx = context_check(track_id, today, root)
    base = session_check(track_id, root)

    checks = {
        "card_or_reason": base["ok"] if taught else True,
        "logged_today": today in log_dates(track_id, root),
        "next_action_set": bool(meta.get("next_action")),
        "context_fresh": ctx["exists"] and ctx["fresh"],
    }
    missing: list[str] = []
    if not checks["card_or_reason"]:
        missing.append(
            "no card and no logged reason — add a card or `log --no-cards-reason \"<why>\"`"
        )
    if not checks["logged_today"]:
        missing.append("no Log row dated today — run `log --track <id> --what \"...\" --next \"...\"`")
    if not checks["next_action_set"]:
        missing.append("next_action is empty — set `--next \"<what to do next time>\"` when you log")
    if not checks["context_fresh"]:
        if not ctx["exists"]:
            missing.append("CONTEXT.md missing — write the memory digest (with `last_updated: <today>`)")
        else:
            missing.append(
                f"CONTEXT.md not updated today (last_updated: {ctx['last_updated']}) — refresh it"
            )

    warnings: list[str] = []
    if ctx["over_budget"]:
        warnings.append(
            f"CONTEXT.md is {ctx['size_chars']} chars (> {CONTEXT_MAX_CHARS}); "
            "summarize old sticking points into a short 'resolved' line so it stays a digest"
        )

    return {
        "ok": all(checks.values()),
        "taught": taught,
        "checks": checks,
        "missing": missing,
        "warnings": warnings,
        "context": ctx,
    }


def _read_review_log(track_id: str, root: Path | None = None) -> list[dict]:
    path = review_log_path(track_id, root)
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def progress(
    track: str = "all", today: str | None = None, root: Path | None = None
) -> dict:
    """Three retention numbers per track — proof the system is working.

    cards_total / cards_graduated (FSRS interval > 21 days) / 7-day review accuracy.
    Pure read over card files + review-state.json + review-log.jsonl. No dashboard.
    """
    today = _today_str(today)
    if track and track != "all":
        if not track_md_path(track, root).exists():
            raise ValueError(f"unknown track '{track}'")
        track_ids = [track]
    else:
        track_ids = [rec["id"] for rec in rebuild_registry(root)["tracks"]]

    cutoff = datetime.strptime(today, "%Y-%m-%d").date() - timedelta(days=7)
    rows = []
    for tid in track_ids:
        state = load_review_state(tid, root)
        cards_total = len(list_card_ids(tid, root))
        graduated = 0
        for entry in state.values():
            if not isinstance(entry, dict):
                continue
            due, lr = entry.get("due"), entry.get("last_review")
            if due and lr:
                try:
                    iv = (
                        datetime.strptime(due, "%Y-%m-%d").date()
                        - datetime.strptime(lr, "%Y-%m-%d").date()
                    ).days
                    if iv > 21:
                        graduated += 1
                except ValueError:
                    pass
        recent = []
        for r in _read_review_log(tid, root):
            d = r.get("date")
            try:
                if d and datetime.strptime(d, "%Y-%m-%d").date() >= cutoff:
                    recent.append(r)
            except ValueError:
                pass
        good = sum(
            1 for r in recent if isinstance(r.get("grade"), int) and r["grade"] >= 3
        )
        rows.append(
            {
                "track": tid,
                "cards_total": cards_total,
                "cards_graduated": graduated,
                "reviews_7d": len(recent),
                "accuracy_7d": round(good / len(recent), 2) if recent else None,
            }
        )
    return {"today": today, "tracks": rows}


def questions_log_path(track_id: str, root: Path | None = None) -> Path:
    return track_dir(track_id, root) / "questions-log.jsonl"


def log_question(
    track_id: str,
    concept: str,
    question: str,
    term: str | None = None,
    today: str | None = None,
    root: Path | None = None,
) -> dict:
    """Append one ad-hoc learner question to questions-log.jsonl (append-only).

    `concept` is the clustering key (what the question is about); `term` is the
    specific word, if any. This is the quantitative layer behind the markdown
    consolidation — it lets `questions` rank where the learner asked most.
    Best-effort: a logging failure must not break the conversation.
    """
    if not track_md_path(track_id, root).exists():
        raise ValueError(f"unknown track '{track_id}'")
    today = _today_str(today)
    entry = {
        "date": today,
        "concept": (concept or "(uncategorized)").strip() or "(uncategorized)",
        "question": (question or "").strip(),
    }
    if term:
        entry["term"] = term.strip()
    try:
        path = questions_log_path(track_id, root)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as exc:  # pragma: no cover - defensive
        _warn(f"could not append questions-log for '{track_id}' ({exc}); continuing")
    return entry


def questions_stats(
    track: str = "all", today: str | None = None, root: Path | None = None
) -> dict:
    """Where did the learner ask most? Per-concept counts ranked desc.

    Pure read over questions-log.jsonl. The drill-down heatmap: a concept asked
    many times is a weak/important spot. Hot concepts (count >= 3) are flagged.
    """
    today = _today_str(today)
    if track and track != "all":
        if not track_md_path(track, root).exists():
            raise ValueError(f"unknown track '{track}'")
        track_ids = [track]
    else:
        track_ids = [rec["id"] for rec in rebuild_registry(root)["tracks"]]

    rows = []
    for tid in track_ids:
        entries = []
        path = questions_log_path(tid, root)
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        by_concept: dict[str, dict] = {}
        for e in entries:
            c = e.get("concept") or "(uncategorized)"
            slot = by_concept.setdefault(
                c, {"concept": c, "count": 0, "last_asked": None, "terms": []}
            )
            slot["count"] += 1
            d = e.get("date")
            if d and (slot["last_asked"] is None or d > slot["last_asked"]):
                slot["last_asked"] = d
            t = e.get("term")
            if t and t not in slot["terms"]:
                slot["terms"].append(t)
        ranked = sorted(
            by_concept.values(), key=lambda s: (-s["count"], s["concept"])
        )
        for s in ranked:
            s["hot"] = s["count"] >= 3
        rows.append({"track": tid, "total": len(entries), "by_concept": ranked})
    return {"today": today, "tracks": rows}


def ingest_check(track_id: str, root: Path | None = None) -> dict:
    """Deterministic pre-flight gate the `learn` skill MUST pass before INGEST.

    Enforces the things the model tends to skip: the track exists, its MISSION is
    actually filled (not the stub), and it is active. Returns {ready, blockers, ...}
    so the skill can hard-stop and resolve blockers (fill MISSION, etc.) instead of
    free-wheeling straight into card generation.
    """
    if not track_md_path(track_id, root).exists():
        return {
            "track": track_id,
            "ready": False,
            "blockers": ["track does not exist — CREATE it first"],
            "mission_present": False,
            "pedagogy": None,
            "mode": None,
        }
    meta = read_track(track_id, root)
    miss = mission_present(track_id, root)
    status = meta.get("status")
    blockers: list[str] = []
    if not miss:
        blockers.append(
            "MISSION.md is still a stub — interview the learner and fill the 'why' "
            "before any teaching"
        )
    if status not in ("active", None):
        blockers.append(f"track status is '{status}', not active")
    return {
        "track": track_id,
        "ready": not blockers,
        "blockers": blockers,
        "mission_present": miss,
        "pedagogy": meta.get("pedagogy"),
        "mode": meta.get("mode"),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_json(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="learn-everything track/registry IO layer")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("create-track", help="scaffold a new track")
    sp.add_argument("--id", required=True)
    sp.add_argument("--title", required=True)
    sp.add_argument("--mode", required=True)
    sp.add_argument("--pedagogy", required=True)
    sp.add_argument("--deadline", default=None)
    sp.add_argument("--goal", default="")

    sub.add_parser("rebuild", help="rebuild registry.json from TRACK.md files")

    sp = sub.add_parser("status", help="print status board")
    sp.add_argument("--today", default=None)

    sp = sub.add_parser(
        "nudge",
        help="ONE plain human line of what's due (for a daily note / cron / scheduled agent)",
    )
    sp.add_argument("--today", default=None)

    sp = sub.add_parser(
        "leeches", help="cards that keep failing (lapses >= 3) — re-teach, don't re-quiz"
    )
    sp.add_argument("--track", required=True)

    sp = sub.add_parser("next-card-id", help="print next card id for a track")
    sp.add_argument("--track", required=True)

    sp = sub.add_parser(
        "set-prefs", help="adjust a track's priority (goal-weight) / time (minutes per new block)"
    )
    sp.add_argument("--track", required=True)
    sp.add_argument("--goal-weight", type=float, default=None, dest="goal_weight")
    sp.add_argument(
        "--minutes-per-new-block", type=int, default=None, dest="minutes_per_new_block"
    )

    sp = sub.add_parser(
        "ingest-check", help="pre-flight gate for INGEST (track ready? MISSION filled?)"
    )
    sp.add_argument("--track", required=True)

    sp = sub.add_parser(
        "session-check", help="did this session leave a card or a logged reason?"
    )
    sp.add_argument("--track", required=True)
    sp.add_argument(
        "--strict",
        action="store_true",
        help="full session-close gate: card/reason + log-today + next_action + fresh CONTEXT.md",
    )
    sp.add_argument(
        "--review",
        action="store_true",
        help="with --strict: a review/admin session (no new card expected)",
    )

    sp = sub.add_parser(
        "progress", help="3 retention numbers per track (total / graduated / 7-day accuracy)"
    )
    sp.add_argument("--track", default="all")
    sp.add_argument("--today", default=None)

    sp = sub.add_parser("log-question", help="record one ad-hoc learner question")
    sp.add_argument("--track", required=True)
    sp.add_argument("--concept", required=True, help="what the question is about (clustering key)")
    sp.add_argument("--question", required=True)
    sp.add_argument("--term", default=None, help="the specific term asked about, if any")
    sp.add_argument("--today", default=None)

    sp = sub.add_parser(
        "questions", help="where the learner asked most — per-concept counts, ranked"
    )
    sp.add_argument("--track", default="all")
    sp.add_argument("--today", default=None)

    sp = sub.add_parser("add-card", help="add a card to a track")
    sp.add_argument("--track", required=True)
    sp.add_argument("--question", required=True)
    sp.add_argument("--answer", required=True)
    sp.add_argument("--tags", default="")
    sp.add_argument("--today", default=None)
    sp.add_argument(
        "--source", default="", help="provenance: note path / url / page this card came from"
    )

    sp = sub.add_parser(
        "add-cards",
        help="add a batch of approved cards (JSON array on stdin), all-or-nothing",
    )
    sp.add_argument("--track", required=True)
    sp.add_argument("--today", default=None)

    sp = sub.add_parser("due", help="list due cards")
    sp.add_argument("--track", default="all")
    sp.add_argument("--today", default=None)

    sp = sub.add_parser(
        "plan-day", help="ranked, time-boxed daily plan across active tracks"
    )
    sp.add_argument("--today", default=None)
    sp.add_argument("--minutes", type=int, default=None, help="time budget (default 60)")
    sp.add_argument(
        "--energy", default="normal", choices=["low", "normal", "high"]
    )

    sp = sub.add_parser("grade", help="grade a card")
    sp.add_argument("--track", required=True)
    sp.add_argument("--card", required=True)
    sp.add_argument("--grade", required=True, type=int)
    sp.add_argument("--today", default=None)

    sp = sub.add_parser("log", help="append a log entry")
    sp.add_argument("--track", required=True)
    sp.add_argument("--what", required=True)
    sp.add_argument("--next", dest="next_action", default=None)
    sp.add_argument("--artifacts", default="")
    sp.add_argument(
        "--no-cards-reason",
        dest="no_cards_reason",
        default=None,
        help="record why a teaching session produced no card (passes session-check)",
    )

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        if args.command == "create-track":
            create_track(
                args.id,
                args.title,
                args.mode,
                args.pedagogy,
                deadline=args.deadline,
                goal=args.goal,
            )
            _print_json(load_registry())
        elif args.command == "rebuild":
            _print_json(rebuild_registry())
        elif args.command == "status":
            _print_json(status_board(args.today))
        elif args.command == "nudge":
            print(nudge(args.today))
        elif args.command == "leeches":
            _print_json(leeches(args.track))
        elif args.command == "next-card-id":
            print(next_card_id(args.track))
        elif args.command == "set-prefs":
            _print_json(
                set_prefs(
                    args.track,
                    goal_weight=args.goal_weight,
                    minutes_per_new_block=args.minutes_per_new_block,
                )
            )
        elif args.command == "ingest-check":
            _print_json(ingest_check(args.track))
        elif args.command == "session-check":
            if args.strict:
                _print_json(session_close_check(args.track, taught=not args.review))
            else:
                _print_json(session_check(args.track))
        elif args.command == "progress":
            _print_json(progress(args.track, args.today))
        elif args.command == "log-question":
            _print_json(
                log_question(
                    args.track, args.concept, args.question,
                    term=args.term, today=args.today,
                )
            )
        elif args.command == "questions":
            _print_json(questions_stats(args.track, args.today))
        elif args.command == "add-card":
            tags = [t.strip() for t in args.tags.split(",") if t.strip()]
            print(
                add_card(
                    args.track,
                    args.question,
                    args.answer,
                    tags=tags,
                    today=args.today,
                    source=args.source,
                )
            )
        elif args.command == "add-cards":
            try:
                cards = json.loads(sys.stdin.read())
            except json.JSONDecodeError as exc:
                print(f"error: invalid JSON on stdin ({exc})", file=sys.stderr)
                return 1
            _print_json(add_cards(args.track, cards, today=args.today))
        elif args.command == "due":
            _print_json(due_cards(args.track, args.today))
        elif args.command == "plan-day":
            _print_json(plan_day(args.today, args.minutes, args.energy))
        elif args.command == "grade":
            new_due = grade_card(args.track, args.card, args.grade, today=args.today)
            print(new_due)
        elif args.command == "log":
            log_entry(
                args.track,
                args.what,
                next_action=args.next_action,
                artifacts=args.artifacts,
                no_cards_reason=args.no_cards_reason,
            )
        else:  # pragma: no cover - argparse enforces choices
            print(f"unknown command: {args.command}", file=sys.stderr)
            return 2
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except ImportError as exc:
        print(f"error: cannot load fsrs scheduler ({exc})", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
