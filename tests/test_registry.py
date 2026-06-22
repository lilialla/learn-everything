#!/usr/bin/env python3
"""Tests for scripts/registry.py — track/registry IO layer.

Operates entirely in tempfile dirs (never touches the real tracks/). Calls the
importable functions directly; grade tests inject a fake scheduler so they do
not depend on a live fsrs.py.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

# Make scripts/ importable regardless of where the test runner is launched.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import registry  # noqa: E402


def _iso(d: date) -> str:
    return d.isoformat()


class RegistryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "tracks").mkdir()
        self.today = _iso(date(2026, 6, 22))
        self.tomorrow = _iso(date(2026, 6, 23))
        self.yesterday = _iso(date(2026, 6, 21))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # -- helpers ----------------------------------------------------------

    def _make_track(self, track_id="python", **kw):
        return registry.create_track(
            track_id,
            kw.get("title", "Learn Python"),
            kw.get("mode", "domain"),
            kw.get("pedagogy", "socratic"),
            deadline=kw.get("deadline"),
            goal=kw.get("goal", "Understand decorators"),
            today=kw.get("today", self.today),
            root=self.root,
        )

    def _registry_json(self):
        return json.loads(
            (self.root / "registry.json").read_text(encoding="utf-8")
        )

    # -- tests ------------------------------------------------------------

    def test_create_track_then_rebuild_has_track_with_zero_cards(self):
        self._make_track()
        reg = registry.rebuild_registry(self.root)
        self.assertEqual(len(reg["tracks"]), 1)
        rec = reg["tracks"][0]
        self.assertEqual(rec["id"], "python")
        self.assertEqual(rec["title"], "Learn Python")
        self.assertEqual(rec["mode"], "domain")
        self.assertEqual(rec["pedagogy"], "socratic")
        self.assertEqual(rec["status"], "active")
        self.assertEqual(rec["cards_total"], 0)
        # Persisted file matches the returned dict.
        self.assertEqual(self._registry_json(), reg)

    def test_create_track_rejects_duplicate_id(self):
        self._make_track()
        with self.assertRaises(ValueError):
            self._make_track()

    def test_next_card_id_progression(self):
        self._make_track()
        self.assertEqual(registry.next_card_id("python", self.root), "card-0001")
        registry.add_card(
            "python", "Q1", "A1", today=self.today, root=self.root
        )
        registry.add_card(
            "python", "Q2", "A2", today=self.today, root=self.root
        )
        self.assertEqual(registry.next_card_id("python", self.root), "card-0003")

    def test_add_card_writes_file_and_seeds_state(self):
        self._make_track()
        card_id = registry.add_card(
            "python",
            "What is a closure?",
            "A function capturing its enclosing scope.",
            tags=["fp", "scope"],
            today=self.today,
            root=self.root,
        )
        self.assertEqual(card_id, "card-0001")

        card_path = self.root / "tracks" / "python" / "cards" / "card-0001.md"
        self.assertTrue(card_path.exists())
        text = card_path.read_text(encoding="utf-8")
        # Obsidian spaced-repetition compatible: question, lone `?`, answer,
        # under a #flashcards/<track> subdeck tag.
        self.assertIn("What is a closure?", text)
        self.assertIn("\n?\n", text)
        self.assertIn("A function capturing its enclosing scope.", text)
        self.assertIn("#flashcards/python", text)
        self.assertIn("id: card-0001", text)
        self.assertIn("fp", text)
        # read_card_question parses the multi-line format back out.
        self.assertEqual(
            registry.read_card_question("python", "card-0001", self.root),
            "What is a closure?",
        )

        state = json.loads(
            (self.root / "tracks" / "python" / "review-state.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("card-0001", state)
        self.assertEqual(state["card-0001"]["state"], "new")
        self.assertEqual(state["card-0001"]["due"], self.today)

    def test_due_filters_by_today(self):
        self._make_track()
        registry.add_card(
            "python", "Q1", "A1", today=self.today, root=self.root
        )
        # Card seeded due=today. With today=tomorrow it is due (due<=today).
        due_tomorrow = registry.due_cards("all", self.tomorrow, self.root)
        self.assertEqual(len(due_tomorrow), 1)
        self.assertEqual(due_tomorrow[0]["card"], "card-0001")
        self.assertEqual(due_tomorrow[0]["track"], "python")
        self.assertEqual(due_tomorrow[0]["question"], "Q1")
        # With today=yesterday, the card (due=today) is not yet due.
        due_yesterday = registry.due_cards("all", self.yesterday, self.root)
        self.assertEqual(due_yesterday, [])

    def test_due_per_track_filter(self):
        self._make_track("python")
        self._make_track("rust", title="Learn Rust")
        registry.add_card("python", "PQ", "PA", today=self.today, root=self.root)
        registry.add_card("rust", "RQ", "RA", today=self.today, root=self.root)
        only_rust = registry.due_cards("rust", self.tomorrow, self.root)
        self.assertEqual([c["track"] for c in only_rust], ["rust"])

    def test_rebuild_reconstructs_after_registry_deleted(self):
        self._make_track()
        registry.add_card("python", "Q", "A", today=self.today, root=self.root)
        reg_path = self.root / "registry.json"
        self.assertTrue(reg_path.exists())
        reg_path.unlink()  # delete the cache
        # load_registry must reconstruct from TRACK.md.
        reg = registry.load_registry(self.root)
        self.assertTrue(reg_path.exists())
        self.assertEqual(len(reg["tracks"]), 1)
        self.assertEqual(reg["tracks"][0]["id"], "python")
        self.assertEqual(reg["tracks"][0]["cards_total"], 1)

    def test_corrupt_registry_rebuilds(self):
        self._make_track()
        (self.root / "registry.json").write_text("{ not json", encoding="utf-8")
        reg = registry.load_registry(self.root)
        self.assertEqual(len(reg["tracks"]), 1)

    def test_corrupt_review_state_does_not_crash_due_or_status(self):
        self._make_track()
        registry.add_card("python", "Q", "A", today=self.today, root=self.root)
        rs_path = self.root / "tracks" / "python" / "review-state.json"
        rs_path.write_text("{ corrupt", encoding="utf-8")
        # due treats cards as new (due now) without crashing.
        due = registry.due_cards("all", self.today, self.root)
        self.assertEqual(len(due), 1)
        # status board also runs.
        board = registry.status_board(self.today, self.root)
        self.assertEqual(board["tracks"][0]["cards_due_today"], 1)

    def test_status_board_flags_deadline_and_stale(self):
        # deadline in 5 days; last_active far in the past via log not called.
        self._make_track(deadline=_iso(date(2026, 6, 27)))
        board = registry.status_board(self.today, self.root)
        rec = board["tracks"][0]
        self.assertEqual(rec["days_to_deadline"], 5)
        self.assertFalse(rec["stale"])  # just created today
        # A track created 10 days ago with no activity is stale.
        old = _iso(date(2026, 6, 12))
        self._make_track("old", title="Old", today=old)
        board2 = registry.status_board(self.today, self.root)
        old_rec = next(t for t in board2["tracks"] if t["id"] == "old")
        self.assertTrue(old_rec["stale"])

    def test_grade_with_injected_scheduler_writes_state(self):
        self._make_track()
        registry.add_card("python", "Q", "A", today=self.today, root=self.root)

        captured = {}

        def fake_schedule(state, grade, now):
            captured["state"] = state
            captured["grade"] = grade
            captured["now"] = now
            return {
                "stability": 5.0,
                "difficulty": 5.0,
                "due": self.tomorrow,
                "reps": 1,
                "lapses": 0,
                "last_review": now,
                "state": "review",
            }

        new_due = registry.grade_card(
            "python",
            "card-0001",
            3,
            today=self.today,
            root=self.root,
            scheduler=fake_schedule,
        )
        self.assertEqual(new_due, self.tomorrow)
        # New card -> prior state passed to fsrs is None.
        self.assertIsNone(captured["state"])
        self.assertEqual(captured["grade"], 3)

        state = json.loads(
            (self.root / "tracks" / "python" / "review-state.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(state["card-0001"]["state"], "review")
        self.assertEqual(state["card-0001"]["due"], self.tomorrow)
        # last_active bumped on the track.
        meta = registry.read_track("python", self.root)
        self.assertEqual(meta["last_active"], self.today)

    def test_grade_rejects_bad_grade(self):
        self._make_track()
        registry.add_card("python", "Q", "A", today=self.today, root=self.root)
        with self.assertRaises(ValueError):
            registry.grade_card(
                "python", "card-0001", 9, today=self.today, root=self.root,
                scheduler=lambda *a: {"due": self.today},
            )

    def test_grade_unknown_card_errors(self):
        self._make_track()
        with self.assertRaises(ValueError):
            registry.grade_card(
                "python", "card-9999", 3, today=self.today, root=self.root,
                scheduler=lambda *a: {"due": self.today},
            )

    def test_log_appends_row_and_updates_meta(self):
        self._make_track()
        registry.log_entry(
            "python",
            "Studied closures",
            next_action="Do exercises",
            artifacts="notes/closures.md",
            today=self.today,
            root=self.root,
        )
        track_md = (self.root / "tracks" / "python" / "TRACK.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Studied closures", track_md)
        self.assertIn("notes/closures.md", track_md)
        meta = registry.read_track("python", self.root)
        self.assertEqual(meta["last_active"], self.today)
        self.assertEqual(meta["next_action"], "Do exercises")

    def test_frontmatter_roundtrip_null_deadline(self):
        self._make_track(deadline=None)
        meta = registry.read_track("python", self.root)
        self.assertIsNone(meta["deadline"])
        self.assertEqual(meta["status"], "active")


if __name__ == "__main__":
    unittest.main()
