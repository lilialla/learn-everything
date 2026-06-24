#!/usr/bin/env python3
"""Tests for adapters/fsrs_optimize — personalized FSRS-weights adapter.

The PURE stdlib pieces (log parsing, revlog reshaping, weights round-trip) run
with nothing installed. The actual weight FIT self-skips when fsrs-optimizer is
absent, so core CI stays green with no optional deps.
"""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)  # so `adapters` and `scripts` import
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

from adapters.fsrs_optimize import optimize  # noqa: E402

_HAS_OPTIMIZER = importlib.util.find_spec("fsrs_optimizer") is not None


def _make_track(root: Path, track_id: str, log_rows: list[dict]) -> None:
    """Create a minimal track dir with a TRACK.md and a review-log.jsonl."""
    tdir = root / "tracks" / track_id
    tdir.mkdir(parents=True, exist_ok=True)
    (tdir / "TRACK.md").write_text("---\ntitle: t\n---\n", encoding="utf-8")
    with (tdir / "review-log.jsonl").open("w", encoding="utf-8") as fh:
        for r in log_rows:
            fh.write(json.dumps(r) + "\n")


class TestReadReviewLog(unittest.TestCase):
    def test_missing_log_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "tracks" / "t1").mkdir(parents=True)
            self.assertEqual(optimize.read_review_log("t1", root), [])

    def test_skips_blank_and_malformed_lines(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            tdir = root / "tracks" / "t1"
            tdir.mkdir(parents=True)
            (tdir / "review-log.jsonl").write_text(
                '{"date":"2026-06-01","card":"card-0001","grade":3}\n'
                "\n"
                "not json at all\n"
                '{"date":"2026-06-02","card":"card-0001","grade":4}\n',
                encoding="utf-8",
            )
            rows = optimize.read_review_log("t1", root)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["card"], "card-0001")


class TestBuildRevlogRows(unittest.TestCase):
    def test_first_review_is_new_then_review(self):
        entries = [
            {"date": "2026-06-01", "card": "c1", "grade": 3},
            {"date": "2026-06-03", "card": "c1", "grade": 4},
        ]
        rows = optimize.build_revlog_rows(entries, "trk")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["review_state"], optimize._STATE_NEW)
        self.assertEqual(rows[1]["review_state"], optimize._STATE_REVIEW)
        # card_id is namespaced so an --track all fit can't collide.
        self.assertTrue(rows[0]["card_id"].startswith("trk:"))
        # review_time strictly increasing for one card over distinct dates.
        self.assertLess(rows[0]["review_time"], rows[1]["review_time"])

    def test_lapse_after_review_is_relearning(self):
        entries = [
            {"date": "2026-06-01", "card": "c1", "grade": 3},
            {"date": "2026-06-05", "card": "c1", "grade": 1},
        ]
        rows = optimize.build_revlog_rows(entries, "trk")
        self.assertEqual(rows[1]["review_state"], optimize._STATE_RELEARNING)

    def test_drops_invalid_rows(self):
        entries = [
            {"date": "2026-06-01", "card": "c1", "grade": 3},
            {"date": "2026-06-01", "grade": 3},  # no card
            {"card": "c2", "grade": 3},  # no date
            {"date": "2026-06-01", "card": "c3", "grade": 9},  # bad grade
        ]
        rows = optimize.build_revlog_rows(entries, "trk")
        self.assertEqual(len(rows), 1)

    def test_global_ordering_by_review_time(self):
        entries = [
            {"date": "2026-06-05", "card": "c2", "grade": 3},
            {"date": "2026-06-01", "card": "c1", "grade": 3},
        ]
        rows = optimize.build_revlog_rows(entries, "trk")
        times = [r["review_time"] for r in rows]
        self.assertEqual(times, sorted(times))


class TestWriteWeights(unittest.TestCase):
    def test_round_trip(self):
        weights = [0.1 * i for i in range(optimize.WEIGHTS_LEN)]
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "fsrs-weights.json"
            optimize.write_weights(out, weights, {"scope": "global"})
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(len(data["weights"]), optimize.WEIGHTS_LEN)
            self.assertEqual(data["provenance"]["scope"], "global")

    def test_rejects_wrong_length(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "fsrs-weights.json"
            with self.assertRaises(optimize.OptimizeError):
                optimize.write_weights(out, [1.0, 2.0], {})


class TestRunGating(unittest.TestCase):
    def test_refuses_below_min_reviews(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_track(
                root,
                "t1",
                [{"date": "2026-06-01", "card": "c1", "grade": 3}],
            )
            with self.assertRaises(optimize.OptimizeError) as ctx:
                optimize.run("t1", min_reviews=200, root=root)
            self.assertIn("need at least 200", str(ctx.exception))


@unittest.skipUnless(
    _HAS_OPTIMIZER, "fsrs-optimizer not installed; skipping live-fit test"
)
class TestLiveFit(unittest.TestCase):
    def test_fit_writes_21_weights(self):
        # Synthetic but plausible history: enough reviews to clear the floor.
        entries = []
        for c in range(30):
            for day, grade in enumerate([3, 3, 4, 3, 2, 3, 4, 3], start=1):
                entries.append(
                    {
                        "date": f"2026-06-{day:02d}",
                        "card": f"c{c}",
                        "grade": grade,
                    }
                )
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_track(root, "t1", entries)
            out = optimize.run("t1", min_reviews=50, root=root)
            data = json.loads(Path(out).read_text(encoding="utf-8"))
            self.assertEqual(len(data["weights"]), optimize.WEIGHTS_LEN)


if __name__ == "__main__":
    unittest.main()
