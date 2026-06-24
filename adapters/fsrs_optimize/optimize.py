#!/usr/bin/env python3
"""Fit personalized FSRS-6 weights from review history (OPT-IN, out-of-CORE).

Public surface (stable contract):

    read_review_log(track_id, root=None) -> list[dict]
        Parse one track's tracks/<id>/review-log.jsonl into ordered rows.

    build_revlog_rows(entries, track_id) -> list[dict]
        Reshape grade events into the fsrs-optimizer revlog schema
        (card_id, review_time ms, review_rating, review_state). Pure stdlib.

    fit_weights(rows, *, timezone="UTC") -> tuple[list[float], dict]
        Lazily import fsrs-optimizer/torch and fit the 21-float vector.
        Returns (weights, fit_stats). Raises OptimizeError with a friendly
        install hint if the deps are missing.

    write_weights(out_path, weights, provenance) -> None
        Write the data-only fsrs-weights.json the CORE loader reads.

CLI:
    python3 adapters/fsrs_optimize/optimize.py [--track <id|all>]
                 [--min-reviews 200] [--out <path>] [--timezone UTC]

Design rules (plans/specs/2026-06-22-feature-designs.md, Engine Hardening 2):
  * The CORE algorithm (scripts/fsrs.py) gains no pip import. This adapter
    writes ONLY data: a weights file fsrs.py can OPTIONALLY load.
  * fsrs-optimizer + torch are imported LAZILY inside fit_weights, never at
    module import. A missing dep yields a friendly OptimizeError, never a raw
    ImportError at import time.
  * Gated on real history: refuse below --min-reviews (default 200) and print
    the count we had. Too-few-reviews is a surfaced limit, not a silent fit.
  * Learner review history is private: we only ever read tracks/<id>/ and
    write the weights file; nothing is committed.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone as _tz
from pathlib import Path

# --- CORE import (stdlib-only registry helpers; NO heavy deps) -------------
# Resolve scripts/ relative to the repo root so this runs from anywhere.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "scripts"))

import registry  # noqa: E402  (stdlib-only CORE module)

# fsrs-optimizer / FSRS-6 weight vectors are length 21 (w[0..20]).
WEIGHTS_LEN = 21
WEIGHTS_FILENAME = "fsrs-weights.json"

# Personalized weights are meaningless on a tiny history. The design notes
# ">200 graded reviews to mean anything"; we floor at 200 by default.
DEFAULT_MIN_REVIEWS = 200

# fsrs-optimizer rating values match ours: 1=Again 2=Hard 3=Good 4=Easy.
# review_state values it expects: 0=New 1=Learning 2=Review 3=Relearning.
# Our minimal MVP state machine only has "new"/"review"; we map the FIRST
# review of a card to New(0) and every subsequent one to Review(2) — a lapse
# (grade 1) on a card already in review is the closest we have to Relearning.
_STATE_NEW = 0
_STATE_REVIEW = 2
_STATE_RELEARNING = 3


class OptimizeError(RuntimeError):
    """Raised on missing deps, too-few reviews, or a failed fit."""


# ---------------------------------------------------------------------------
# Pure stdlib pieces (unit-testable with nothing installed)
# ---------------------------------------------------------------------------

def read_review_log(track_id: str, root: Path | None = None) -> list[dict]:
    """Parse tracks/<id>/review-log.jsonl into a list of grade-event dicts.

    Best-effort and forgiving: blank lines and malformed JSON lines are
    skipped (a corrupt history line must not abort the whole fit). Returns
    [] if the log does not exist.
    """
    path = registry.review_log_path(track_id, root)
    if not path.exists():
        return []
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue  # skip a single bad line, keep the rest
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _date_to_review_time_ms(date_str: str, seq: int) -> int:
    """Map a YYYY-MM-DD grade date to a millisecond UTC timestamp.

    Our log records date granularity only (no clock time). fsrs-optimizer
    orders reviews by review_time, so we add `seq` milliseconds to keep
    same-day reviews of one card in their logged order without inventing a
    fake wall-clock time.
    """
    dt = datetime.fromisoformat(date_str).replace(tzinfo=_tz.utc)
    return int(dt.timestamp() * 1000) + seq


def build_revlog_rows(entries: list[dict], track_id: str) -> list[dict]:
    """Reshape grade events into the fsrs-optimizer revlog row schema.

    Input rows are the learn-everything per-track review-log schema written by
    registry.grade_card: {date, card, grade, due, reps, lapses, state}.

    Output rows: {card_id, review_time, review_rating, review_state} where
    review_time is ms and card_id is namespaced "<track>:<card>" so an
    --track all fit never collides ids across tracks.

    Pure stdlib. Rows missing date/card/grade are dropped (can't be used).
    """
    # Order by (card, date) so each card's first valid review becomes New.
    cleaned: list[dict] = []
    for e in entries:
        card = e.get("card")
        date_str = e.get("date")
        grade = e.get("grade")
        if not card or not date_str or grade not in (1, 2, 3, 4):
            continue
        cleaned.append(e)

    # Stable sort by date then by logged order preserves real chronology;
    # Python's sort is stable so equal dates keep file order.
    indexed = list(enumerate(cleaned))
    indexed.sort(key=lambda iv: (iv[1].get("card"), iv[1].get("date"), iv[0]))

    rows: list[dict] = []
    per_card_seen: dict[str, int] = {}
    for orig_idx, e in indexed:
        card = e["card"]
        seen = per_card_seen.get(card, 0)
        per_card_seen[card] = seen + 1
        if seen == 0:
            state = _STATE_NEW
        elif e["grade"] == 1:
            state = _STATE_RELEARNING
        else:
            state = _STATE_REVIEW
        rows.append(
            {
                "card_id": f"{track_id}:{card}",
                "review_time": _date_to_review_time_ms(e["date"], seen),
                "review_rating": int(e["grade"]),
                "review_state": state,
            }
        )

    # Final ordering for the optimizer: by review_time (then card_id) globally.
    rows.sort(key=lambda r: (r["review_time"], r["card_id"]))
    return rows


def _write_revlog_csv(rows: list[dict], csv_path: Path) -> None:
    """Write rows to the revlog.csv schema fsrs-optimizer ingests (stdlib csv)."""
    import csv  # stdlib

    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["card_id", "review_time", "review_rating", "review_state"])
        for r in rows:
            writer.writerow(
                [r["card_id"], r["review_time"], r["review_rating"], r["review_state"]]
            )


def write_weights(out_path: Path, weights: list[float], provenance: dict) -> None:
    """Write the data-only fsrs-weights.json that the CORE loader reads.

    Schema (see scripts/fsrs.py load_weights integration note):
        {"weights": [21 floats], "provenance": {...}}
    """
    if len(weights) != WEIGHTS_LEN:
        raise OptimizeError(
            f"refusing to write a {len(weights)}-length vector; "
            f"expected {WEIGHTS_LEN}"
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"weights": [float(w) for w in weights], "provenance": provenance}
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(out_path)  # atomic on the same filesystem


# ---------------------------------------------------------------------------
# Heavy step: LAZY-import fsrs-optimizer / torch and fit
# ---------------------------------------------------------------------------

_INSTALL_HINT = (
    "personalized FSRS weights need the optional optimizer dependency.\n"
    "  install it with:  pip install -r adapters/fsrs_optimize/requirements.txt\n"
    "  (this pulls fsrs-optimizer + torch; it is intentionally NOT part of the\n"
    "   pip-free CORE — only this opt-in adapter uses it.)"
)


def fit_weights(rows: list[dict], *, timezone: str = "UTC") -> tuple[list[float], dict]:
    """Fit the 21-float FSRS-6 weight vector from revlog rows.

    Lazily imports fsrs-optimizer (and its torch dependency) HERE so importing
    this package stays pip-free. Raises OptimizeError with a friendly install
    hint if the dependency is missing.
    """
    try:
        import fsrs_optimizer  # noqa: F401  (heavy: pulls torch)
    except ImportError as exc:  # friendly, not a raw ImportError to the user
        raise OptimizeError(_INSTALL_HINT) from exc

    import shutil  # stdlib
    import tempfile  # stdlib

    # fsrs-optimizer reads/writes a few files relative to CWD; run it inside a
    # throwaway temp dir so it never litters the repo or the learner's vault.
    work = Path(tempfile.mkdtemp(prefix="fsrs-optimize-"))
    try:
        csv_path = work / "revlog.csv"
        _write_revlog_csv(rows, csv_path)

        optimizer = fsrs_optimizer.Optimizer()
        # The Optimizer reads ./revlog.csv from the current directory.
        shutil.copyfile(csv_path, work / "revlog.csv")
        cwd_before = Path.cwd()
        try:
            import os

            os.chdir(work)
            optimizer.create_time_series(
                timezone=timezone,
                revlog_start_date="2000-01-01",
                next_day_starts_at=4,
                filter_out_suspended_cards=False,
            )
            optimizer.define_model()
            optimizer.pretrain(verbose=False)
            optimizer.train(verbose=False)
        finally:
            import os

            os.chdir(cwd_before)

        weights = [float(w) for w in list(optimizer.w)]
        if len(weights) != WEIGHTS_LEN:
            raise OptimizeError(
                f"optimizer returned {len(weights)} weights; expected {WEIGHTS_LEN}"
            )

        stats = {
            "optimizer": _optimizer_version(),
            "log_loss": _safe_float(getattr(optimizer, "loss", None)),
        }
        return weights, stats
    except OptimizeError:
        raise
    except Exception as exc:  # any optimizer-internal failure -> friendly error
        raise OptimizeError(f"weight fit failed: {exc}") from exc
    finally:
        import shutil as _shutil

        _shutil.rmtree(work, ignore_errors=True)


def _optimizer_version() -> str:
    try:
        from importlib.metadata import version

        return f"fsrs-optimizer=={version('FSRS-Optimizer')}"
    except Exception:
        return "fsrs-optimizer==unknown"


def _safe_float(value) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def _all_track_ids(root: Path | None = None) -> list[str]:
    """List track ids by scanning tracks/ for TRACK.md (stdlib, no registry cache)."""
    tdir = registry.tracks_dir(root)
    if not tdir.exists():
        return []
    ids = []
    for child in sorted(tdir.iterdir()):
        if child.is_dir() and (child / "TRACK.md").exists():
            ids.append(child.name)
    return ids


def _collect_rows(track: str, root: Path | None) -> tuple[list[dict], int, list[str]]:
    """Gather revlog rows for one track id or "all". Returns (rows, n_events, ids)."""
    if track == "all":
        ids = _all_track_ids(root)
    else:
        ids = [track]
    rows: list[dict] = []
    n_events = 0
    for tid in ids:
        entries = read_review_log(tid, root)
        n_events += len(entries)
        rows.extend(build_revlog_rows(entries, tid))
    return rows, n_events, ids


def run(
    track: str = "all",
    *,
    min_reviews: int = DEFAULT_MIN_REVIEWS,
    out: Path | None = None,
    timezone: str = "UTC",
    root: Path | None = None,
) -> Path:
    """Fit and write personalized weights for one track or all. Returns out path.

    Refuses below `min_reviews` (raises OptimizeError naming the count). The
    weights file goes to `out`, or tracks/<id>/fsrs-weights.json for a single
    track, or <root>/fsrs-weights.json (global) for --track all.
    """
    rows, n_events, ids = _collect_rows(track, root)
    n_rows = len(rows)
    if n_rows < min_reviews:
        raise OptimizeError(
            f"only {n_rows} usable graded reviews "
            f"(from {n_events} log events across {len(ids)} track(s)); "
            f"need at least {min_reviews}.\n"
            "Personalized FSRS weights overfit on tiny histories — keep "
            "reviewing with the built-in FSRS-6 defaults and try again later."
        )

    weights, stats = fit_weights(rows, timezone=timezone)

    scope = "global" if track == "all" else track
    if out is None:
        base = registry.repo_root() if root is None else root
        if track == "all":
            out = base / WEIGHTS_FILENAME
        else:
            out = registry.track_dir(track, root) / WEIGHTS_FILENAME

    provenance = {
        "fit_date": datetime.now(_tz.utc).date().isoformat(),
        "scope": scope,
        "tracks": ids,
        "review_count": n_rows,
        "source": "review-log.jsonl",
        **stats,
    }
    write_weights(out, weights, provenance)
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fit personalized FSRS-6 weights from review history (OPT-IN, "
            "dependency-heavy; needs fsrs-optimizer + torch)."
        )
    )
    parser.add_argument(
        "--track",
        default="all",
        help="track id to fit, or 'all' for a global fit across every track "
        "(default: all)",
    )
    parser.add_argument(
        "--min-reviews",
        type=int,
        default=DEFAULT_MIN_REVIEWS,
        help=f"refuse to fit below this many graded reviews "
        f"(default: {DEFAULT_MIN_REVIEWS}; below ~200 weights are meaningless)",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="output weights path (default: tracks/<id>/fsrs-weights.json for "
        "one track, <root>/fsrs-weights.json for --track all)",
    )
    parser.add_argument(
        "--timezone",
        default="UTC",
        help="IANA timezone passed to the optimizer (default: UTC)",
    )
    args = parser.parse_args(argv)

    out = Path(args.out) if args.out else None
    try:
        written = run(
            args.track,
            min_reviews=args.min_reviews,
            out=out,
            timezone=args.timezone,
        )
    except OptimizeError as exc:
        print(f"fsrs-optimize: {exc}", file=sys.stderr)
        return 1

    print(f"fsrs-optimize: wrote personalized weights to {written}")
    print(
        "  fsrs.py will load it automatically if its loader precedence is "
        "wired in (see adapters/fsrs_optimize/README.md integration note)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
