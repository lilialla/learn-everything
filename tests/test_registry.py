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

    def test_status_board_row_carries_actionable_fields(self):
        self._make_track(pedagogy="tutor")
        registry.add_card("python", "Q", "A", today=self.today, root=self.root)
        registry.log_entry(
            "python", "Studied", next_action="Do exercises",
            today=self.today, root=self.root,
        )
        board = registry.status_board(self.today, self.root)
        rec = board["tracks"][0]
        # Fields that make the board a "do this next", not just a list.
        self.assertEqual(rec["mode"], "domain")
        self.assertEqual(rec["pedagogy"], "tutor")
        self.assertEqual(rec["cards_total"], 1)
        self.assertEqual(rec["next_action"], "Do exercises")
        self.assertEqual(rec["last_active"], self.today)
        self.assertIn("stale_days", rec)

    def test_status_board_orders_due_and_deadline_first(self):
        # 'fresh' has no cards, no deadline. 'urgent' has a near deadline.
        # 'reviewy' has cards due today. Order should be urgent, reviewy, fresh.
        self._make_track("fresh", title="Fresh")
        self._make_track("urgent", title="Urgent",
                         deadline=_iso(date(2026, 6, 23)))
        self._make_track("reviewy", title="Reviewy")
        registry.add_card("reviewy", "Q", "A", today=self.today, root=self.root)
        board = registry.status_board(self.today, self.root)
        ids = [t["id"] for t in board["tracks"]]
        self.assertEqual(ids[0], "urgent")  # deadline < 3 days
        self.assertEqual(ids[1], "reviewy")  # cards due today
        self.assertEqual(ids[2], "fresh")

    def test_corrupt_review_state_raises_on_grade(self):
        self._make_track()
        registry.add_card("python", "Q1", "A1", today=self.today, root=self.root)
        registry.add_card("python", "Q2", "A2", today=self.today, root=self.root)
        rs_path = self.root / "tracks" / "python" / "review-state.json"
        rs_path.write_text("{ corrupt", encoding="utf-8")
        # Grading must abort rather than silently zero the other card's state.
        with self.assertRaises(ValueError):
            registry.grade_card(
                "python", "card-0001", 3, today=self.today, root=self.root,
                scheduler=lambda *a: {"due": self.tomorrow},
            )
        # Corrupt file quarantined; no fresh review-state.json clobbering it.
        bad = list((self.root / "tracks" / "python").glob("review-state.json.bad.*"))
        self.assertEqual(len(bad), 1)

    def test_malformed_card_entry_does_not_crash_status(self):
        self._make_track()
        registry.add_card("python", "Q", "A", today=self.today, root=self.root)
        rs_path = self.root / "tracks" / "python" / "review-state.json"
        # A non-dict per-card entry (e.g. hand-edit gone wrong).
        rs_path.write_text(
            json.dumps({"card-0001": "oops"}), encoding="utf-8"
        )
        board = registry.status_board(self.today, self.root)
        # Treated as new -> due now, no AttributeError crash.
        self.assertEqual(board["tracks"][0]["cards_due_today"], 1)

    def test_unknown_frontmatter_key_survives_log(self):
        self._make_track()
        registry.update_track_meta(
            "python", {"custom_field": "keep me"}, root=self.root
        )
        registry.log_entry(
            "python", "did stuff", today=self.today, root=self.root
        )
        meta = registry.read_track("python", self.root)
        self.assertEqual(meta["custom_field"], "keep me")

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

    # -- D2: batch add-cards ---------------------------------------------

    def test_add_cards_batch_all_or_nothing(self):
        self._make_track()
        ids = registry.add_cards(
            "python",
            [
                {"question": "Q1?", "answer": "A1", "tags": ["L1"]},
                {"question": "Q2?", "answer": "A2"},
            ],
            today=self.today,
            root=self.root,
        )
        self.assertEqual(ids, ["card-0001", "card-0002"])
        state = json.loads(
            (self.root / "tracks" / "python" / "review-state.json").read_text("utf-8")
        )
        self.assertEqual(set(state), {"card-0001", "card-0002"})
        # A bad card in the batch rolls back ALL files written this call.
        with self.assertRaises(ValueError):
            registry.add_cards(
                "python",
                [{"question": "Q3?", "answer": "A3"}, {"question": "", "answer": "x"}],
                today=self.today,
                root=self.root,
            )
        # card-0003 (written before the bad one) must have been removed.
        self.assertFalse(
            (self.root / "tracks" / "python" / "cards" / "card-0003.md").exists()
        )

    # -- D3: MISSION scaffolding + signal --------------------------------

    def test_create_track_scaffolds_mission_stub(self):
        self._make_track()
        mp = self.root / "tracks" / "python" / "MISSION.md"
        self.assertTrue(mp.exists())
        # Stub present -> mission_present is False until filled.
        self.assertFalse(registry.mission_present("python", self.root))
        # Remove the stub marker -> counts as filled.
        mp.write_text("# Mission\n\n## Why\nReal reason.\n", encoding="utf-8")
        self.assertTrue(registry.mission_present("python", self.root))

    # -- D4: needs_cards retention signal --------------------------------

    def test_status_board_needs_cards_when_taught_but_no_cards(self):
        # created earlier, then activity later (a taught session), still 0 cards.
        old = _iso(date(2026, 6, 12))
        self._make_track(today=old)
        registry.log_entry(
            "python", "taught a session", today=self.today, root=self.root
        )
        rec = registry.status_board(self.today, self.root)["tracks"][0]
        self.assertTrue(rec["needs_cards"])
        # After a card exists, the nudge clears.
        registry.add_card("python", "Q", "A", today=self.today, root=self.root)
        rec2 = registry.status_board(self.today, self.root)["tracks"][0]
        self.assertFalse(rec2["needs_cards"])

    # -- D5: review-log + due lapses/reps --------------------------------

    def test_grade_appends_review_log_and_due_carries_lapses(self):
        self._make_track()
        registry.add_card("python", "Q", "A", today=self.today, root=self.root)

        def fake_sched(state, grade, now):
            return {
                "stability": 1.0, "difficulty": 5.0, "due": self.tomorrow,
                "reps": 1, "lapses": 1, "last_review": now, "state": "review",
            }

        registry.grade_card(
            "python", "card-0001", 1, today=self.today, root=self.root,
            scheduler=fake_sched,
        )
        log_path = self.root / "tracks" / "python" / "review-log.jsonl"
        self.assertTrue(log_path.exists())
        line = json.loads(log_path.read_text("utf-8").strip().splitlines()[-1])
        self.assertEqual(line["card"], "card-0001")
        self.assertEqual(line["grade"], 1)
        due = registry.due_cards("python", self.tomorrow, self.root)
        self.assertEqual(due[0]["lapses"], 1)
        self.assertEqual(due[0]["reps"], 1)

    # -- D1: plan-day deterministic ranker -------------------------------

    def test_plan_day_ranks_and_timeboxes(self):
        # urgent track (deadline tomorrow) with a due card + next_action.
        self._make_track("urgent", title="Urgent", deadline=self.tomorrow)
        registry.add_card("urgent", "Q", "A", today=self.today, root=self.root)
        registry.log_entry(
            "urgent", "x", next_action="next chapter", today=self.today, root=self.root
        )
        # calm track, no deadline, with a next_action.
        self._make_track("calm", title="Calm")
        registry.log_entry(
            "calm", "x", next_action="read", today=self.today, root=self.root
        )
        plan = registry.plan_day(self.today, minutes=60, root=self.root)
        self.assertIn("scheduled", plan)
        self.assertTrue(plan["scheduled"])
        # The urgent track's blocks outrank the calm track's.
        first = plan["scheduled"][0]
        self.assertEqual(first["track"], "urgent")
        # Deterministic: same inputs -> same output.
        plan2 = registry.plan_day(self.today, minutes=60, root=self.root)
        self.assertEqual(plan, plan2)
        # Total scheduled minutes respect the budget (urgent may force-include).
        self.assertEqual(plan["summary"]["budget_min"], 60)


    # -- D10: read inline / cloze cards without leaking the answer ---------

    def test_read_card_question_inline_and_cloze(self):
        self._make_track()
        cdir = self.root / "tracks" / "python" / "cards"
        cdir.mkdir(parents=True, exist_ok=True)
        (cdir / "card-0001.md").write_text(
            "---\nid: card-0001\ntags: []\n---\n#flashcards/python\n\n"
            "What is a closure::A function capturing its scope\n",
            encoding="utf-8",
        )
        self.assertEqual(
            registry.read_card_question("python", "card-0001", self.root),
            "What is a closure",
        )
        (cdir / "card-0002.md").write_text(
            "---\nid: card-0002\ntags: []\n---\n#flashcards/python\n\n"
            "The capital of France is ==Paris==.\n",
            encoding="utf-8",
        )
        self.assertEqual(
            registry.read_card_question("python", "card-0002", self.root),
            "The capital of France is [...].",
        )

    # -- D11: atomic writes leave no temp turds + correct content ----------

    def test_atomic_write_is_clean(self):
        p = self.root / "sub" / "f.json"
        registry._write_json(p, {"a": 1, "z": "值"})
        self.assertEqual(json.loads(p.read_text("utf-8")), {"a": 1, "z": "值"})
        self.assertEqual(list((self.root / "sub").glob("*.tmp")), [])


    # -- INGEST pre-flight gate (enforce diagnose-first / MISSION-filled) --

    def test_ingest_check_gates_on_mission_and_existence(self):
        # unknown track -> not ready
        r0 = registry.ingest_check("nope", self.root)
        self.assertFalse(r0["ready"])
        self.assertTrue(r0["blockers"])
        # fresh track ships a MISSION stub -> not ready (mission blocker)
        self._make_track()
        r1 = registry.ingest_check("python", self.root)
        self.assertFalse(r1["ready"])
        self.assertFalse(r1["mission_present"])
        self.assertTrue(any("MISSION" in b for b in r1["blockers"]))
        # fill the mission -> ready
        (self.root / "tracks" / "python" / "MISSION.md").write_text(
            "# Mission\n\n## Why\nShip a thing.\n", encoding="utf-8"
        )
        r2 = registry.ingest_check("python", self.root)
        self.assertTrue(r2["ready"])
        self.assertEqual(r2["blockers"], [])
        self.assertTrue(r2["mission_present"])


    # -- P0 Group A: close-the-loop signals ------------------------------

    def test_session_check_requires_card_or_reason(self):
        self._make_track()
        self.assertFalse(registry.session_check("python", self.root)["ok"])
        # a logged reason makes a no-card session legitimate
        registry.log_entry(
            "python", "orientation pass",
            no_cards_reason="first read-through, cards next time",
            today=self.today, root=self.root,
        )
        self.assertTrue(registry.session_check("python", self.root)["ok"])
        # a track with a card passes without any reason
        self._make_track("rust", title="Rust")
        registry.add_card("rust", "Q", "A", today=self.today, root=self.root)
        self.assertTrue(registry.session_check("rust", self.root)["ok"])

    def test_status_due_total_and_resume_pointer_missing(self):
        # taught earlier, active later, but no next_action and no Log row -> pointer missing
        old = _iso(date(2026, 6, 12))
        self._make_track("ghost", today=old)
        registry.update_track_meta("ghost", {"last_active": self.today}, root=self.root)
        board = registry.status_board(self.today, self.root)
        ghost = next(t for t in board["tracks"] if t["id"] == "ghost")
        self.assertTrue(ghost["resume_pointer_missing"])
        # due_total / tracks_with_due reflect due cards
        self._make_track("py2", title="Py2")
        registry.add_card("py2", "Q", "A", today=self.today, root=self.root)
        board2 = registry.status_board(self.tomorrow, self.root)
        self.assertGreaterEqual(board2["due_total"], 1)
        self.assertGreaterEqual(board2["tracks_with_due"], 1)

    def test_progress_three_numbers(self):
        self._make_track()
        registry.add_card("python", "Q", "A", today=self.today, root=self.root)

        def sched(state, grade, now):
            return {
                "stability": 50.0, "difficulty": 5.0, "due": _iso(date(2026, 8, 1)),
                "reps": 1, "lapses": 0, "last_review": now, "state": "review",
            }

        registry.grade_card(
            "python", "card-0001", 4, today=self.today, root=self.root, scheduler=sched
        )
        p = registry.progress("python", self.today, self.root)["tracks"][0]
        self.assertEqual(p["cards_total"], 1)
        self.assertEqual(p["cards_graduated"], 1)  # 2026-08-01 − 2026-06-22 > 21d
        self.assertEqual(p["reviews_7d"], 1)
        self.assertEqual(p["accuracy_7d"], 1.0)


    # -- quantitative question tracking ----------------------------------

    def test_questions_log_and_stats_rank_by_concept(self):
        self._make_track()
        registry.log_question(
            "python", "decorators", "what is a closure?",
            term="closure", today=self.today, root=self.root,
        )
        registry.log_question(
            "python", "decorators", "how does @ work?", today=self.today, root=self.root
        )
        registry.log_question(
            "python", "typing", "what is a Protocol?", today=self.today, root=self.root
        )
        st = registry.questions_stats("python", self.today, self.root)["tracks"][0]
        self.assertEqual(st["total"], 3)
        top = st["by_concept"][0]
        self.assertEqual(top["concept"], "decorators")
        self.assertEqual(top["count"], 2)
        self.assertIn("closure", top["terms"])
        self.assertFalse(top["hot"])  # 2 < 3
        with self.assertRaises(ValueError):
            registry.questions_stats("nope", self.today, self.root)


if __name__ == "__main__":
    unittest.main()
