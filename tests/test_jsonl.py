from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import jsonl  # noqa: E402


class JsonlTest(unittest.TestCase):
    def test_append_and_read_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "events.jsonl"
            jsonl.append_jsonl(path, {"a": 1})
            jsonl.append_jsonl(path, {"b": "值"})
            self.assertEqual(jsonl.read_jsonl(path), [{"a": 1}, {"b": "值"}])

    def test_read_jsonl_skips_bad_and_non_object_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text('{"ok": true}\nnot json\n[]\n\n', encoding="utf-8")
            self.assertEqual(jsonl.read_jsonl(path), [{"ok": True}])

    def test_read_jsonl_strict_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text("not json\n", encoding="utf-8")
            with self.assertRaises(Exception):
                jsonl.read_jsonl(path, skip_bad=False)
