#!/usr/bin/env python3
"""Behavioral-invariant tests for the FSRS-6 scheduler.

These tests assert BEHAVIORAL INVARIANTS, not exact reference numbers.
Numeric parity with py-fsrs is deferred (see scripts/fsrs.py header).
"""

import json
import os
import subprocess
import sys
import unittest
from datetime import date

# Make scripts/ importable when running from repo root.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import fsrs  # noqa: E402

NOW = date(2026, 6, 22)
FSRS_PY = os.path.join(REPO_ROOT, "scripts", "fsrs.py")


def schedule_new(grade, now=NOW):
    """Schedule a brand-new card with the given first grade."""
    return fsrs.schedule(None, grade, now)


class TestNewCard(unittest.TestCase):
    def test_determinism(self):
        # (a) same input -> same output
        a = schedule_new(3)
        b = schedule_new(3)
        self.assertEqual(a, b)

    def test_grade_ordering_intervals(self):
        # (b) interval(Again) < interval(Hard) <= interval(Good) <= interval(Easy)
        # Use a shared prior state so the comparison is apples-to-apples.
        prior = schedule_new(3)
        prior_for_review = dict(prior)
        # Pretend a few days passed before the next review.
        review_day = date(2026, 6, 25)

        def interval(grade):
            new = fsrs.schedule(dict(prior_for_review), grade, review_day)
            return (date.fromisoformat(new["due"]) - review_day).days

        again = interval(1)
        hard = interval(2)
        good = interval(3)
        easy = interval(4)
        self.assertLess(again, hard)
        self.assertLessEqual(hard, good)
        self.assertLessEqual(good, easy)

    def test_again_increments_lapses(self):
        # (c) Again increments lapses
        prior = schedule_new(3)  # lapses == 0
        self.assertEqual(prior["lapses"], 0)
        lapsed = fsrs.schedule(dict(prior), 1, date(2026, 6, 25))
        self.assertEqual(lapsed["lapses"], prior["lapses"] + 1)

    def test_difficulty_within_bounds(self):
        # (d) difficulty stays within [1, 10] for every grade and across reviews.
        for grade in (1, 2, 3, 4):
            s = schedule_new(grade)
            self.assertGreaterEqual(s["difficulty"], 1.0)
            self.assertLessEqual(s["difficulty"], 10.0)
            # Drive it hard toward extremes over many reviews.
            day = NOW
            for _ in range(20):
                day = date.fromisoformat(s["due"])
                s = fsrs.schedule(dict(s), grade, day)
                self.assertGreaterEqual(s["difficulty"], 1.0)
                self.assertLessEqual(s["difficulty"], 10.0)

    def test_due_strictly_after_now_for_success(self):
        # (e) due is strictly after --now for grade >= 2
        for grade in (2, 3, 4):
            s = schedule_new(grade)
            self.assertGreater(date.fromisoformat(s["due"]), NOW)

    def test_state_transitions_to_review(self):
        s = schedule_new(3)
        self.assertEqual(s["state"], "review")
        self.assertEqual(s["reps"], 1)


class TestSchedulePurity(unittest.TestCase):
    def test_does_not_mutate_input(self):
        prior = schedule_new(3)
        snapshot = dict(prior)
        fsrs.schedule(prior, 4, date(2026, 6, 30))
        self.assertEqual(prior, snapshot)


class TestInvalidGrade(unittest.TestCase):
    def test_schedule_rejects_bad_grade(self):
        with self.assertRaises(ValueError):
            fsrs.schedule(None, 0, NOW)
        with self.assertRaises(ValueError):
            fsrs.schedule(None, 5, NOW)


class TestCLI(unittest.TestCase):
    def _run(self, args):
        return subprocess.run(
            [sys.executable, FSRS_PY] + args,
            capture_output=True,
            text=True,
        )

    def test_cli_new_card(self):
        res = self._run(["schedule", "--state", "-", "--grade", "3", "--now", "2026-06-22"])
        self.assertEqual(res.returncode, 0, res.stderr)
        out = json.loads(res.stdout)
        self.assertEqual(out["state"], "review")
        self.assertEqual(out["reps"], 1)
        self.assertIn("due", out)

    def test_cli_invalid_grade_zero(self):
        # (f) invalid grade exits non-zero
        res = self._run(["schedule", "--state", "-", "--grade", "0", "--now", "2026-06-22"])
        self.assertNotEqual(res.returncode, 0)

    def test_cli_invalid_grade_five(self):
        res = self._run(["schedule", "--state", "-", "--grade", "5", "--now", "2026-06-22"])
        self.assertNotEqual(res.returncode, 0)

    def test_cli_roundtrip_existing_state(self):
        first = self._run(["schedule", "--state", "-", "--grade", "3", "--now", "2026-06-22"])
        state = first.stdout.strip()
        second = self._run(["schedule", "--state", state, "--grade", "3", "--now", "2026-06-25"])
        self.assertEqual(second.returncode, 0, second.stderr)
        out = json.loads(second.stdout)
        self.assertEqual(out["reps"], 2)


class TestLoadWeights(unittest.TestCase):
    def test_missing_and_malformed_return_none(self):
        self.assertIsNone(fsrs.load_weights("/no/such/file.json"))
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            bad = os.path.join(d, "w.json")
            with open(bad, "w") as fh:
                fh.write('{"weights": [1, 2, 3]}')  # wrong length
            self.assertIsNone(fsrs.load_weights(bad))

    def test_valid_weights_loaded_and_applied(self):
        import tempfile
        custom = [0.4] * 21  # valid 21-float vector, different from defaults
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "fsrs-weights.json")
            with open(p, "w") as fh:
                json.dump({"weights": custom}, fh)
            loaded = fsrs.load_weights(p)
            self.assertEqual(loaded, custom)
        # custom weights change scheduling vs the built-in defaults
        d0 = fsrs.schedule(None, 3, date(2026, 6, 22))
        d1 = fsrs.schedule(None, 3, date(2026, 6, 22), w=custom)
        self.assertNotEqual(d0["stability"], d1["stability"])


if __name__ == "__main__":
    unittest.main()
