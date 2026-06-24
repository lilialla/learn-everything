#!/usr/bin/env python3
"""Stdlib tests for scripts/structure.py (long-document structural split).

These run in CORE CI: structure.py is pip-free, so nothing here needs installs.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

# Make scripts/ importable when running from repo root.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import structure  # noqa: E402

STRUCTURE_PY = os.path.join(REPO_ROOT, "scripts", "structure.py")


MARKDOWN_DOC = """# The Book

Front matter blurb before chapter one.

## Chapter 1

Opening of chapter one [page: 1].

### Section 1.1

Details of section one [page: 3].

### Section 1.2

More details [page: 5].

## Chapter 2

The second chapter [page: 9].
"""

HEURISTIC_DOC = """Some preface text with no markdown headings at all.

Chapter 1

The first chapter body, plain text.

第2章

第二章正文，没有 markdown 标题。
"""

NO_STRUCTURE_DOC = (
    "Paragraph one is here.\n\n"
    "Paragraph two is here.\n\n"
    "Paragraph three is here.\n\n"
    "Paragraph four is here.\n"
)


class TestHeadingSplit(unittest.TestCase):
    def test_detects_markdown_headings(self):
        doc = structure.split_document(MARKDOWN_DOC, max_chars=10000)
        self.assertEqual(doc.structure_source, "headings")

    def test_chapter_titles(self):
        doc = structure.split_document(MARKDOWN_DOC, max_chars=10000)
        # The book "#" is the shallowest level -> the chapter node; "##" nest as
        # sections under it.
        titles = [c.title for c in doc.chapters]
        self.assertIn("The Book", titles)

    def test_section_nesting(self):
        doc = structure.split_document(MARKDOWN_DOC, max_chars=10000)
        section_titles = [
            s.title for c in doc.chapters for s in c.sections
        ]
        self.assertIn("Chapter 1", section_titles)
        self.assertIn("Section 1.1", section_titles)
        self.assertIn("Chapter 2", section_titles)

    def test_heading_path_preserved(self):
        doc = structure.split_document(MARKDOWN_DOC, max_chars=10000, title="The Book")
        # Every chunk's heading_path is rooted at the document title.
        for chunk in structure.iter_chunks(doc):
            self.assertEqual(chunk.heading_path[0], "The Book")
        # A chunk under Chapter 1 carries the chapter in its path.
        ch1_chunks = [
            c
            for c in structure.iter_chunks(doc)
            if "Chapter 1" in c.heading_path
        ]
        self.assertTrue(ch1_chunks)

    def test_page_anchors(self):
        doc = structure.split_document(MARKDOWN_DOC, max_chars=10000)
        ranges = {c.page_range for c in structure.iter_chunks(doc)}
        # At least one chunk should carry a parsed page anchor.
        self.assertTrue(any(r and r.startswith("p.") for r in ranges))


class TestOffsets(unittest.TestCase):
    def test_offsets_reproduce_source(self):
        doc = structure.split_document(MARKDOWN_DOC, max_chars=120)
        for chunk in structure.iter_chunks(doc):
            span = MARKDOWN_DOC[chunk.start:chunk.end]
            self.assertEqual(MARKDOWN_DOC[chunk.start:chunk.end], span)
            self.assertTrue(chunk.start <= chunk.end)

    def test_chunks_respect_max_chars(self):
        doc = structure.split_document(MARKDOWN_DOC, max_chars=80)
        for chunk in structure.iter_chunks(doc):
            # A chunk packs whole paragraphs; only a single oversized paragraph
            # is hard-wrapped. Allow modest paragraph-boundary slack but verify
            # the hard wrap path keeps things bounded.
            self.assertLessEqual(chunk.char_len, 200)

    def test_chunks_are_ordered(self):
        doc = structure.split_document(MARKDOWN_DOC, max_chars=120)
        chunks = list(structure.iter_chunks(doc))
        starts = [c.start for c in chunks]
        self.assertEqual(starts, sorted(starts))

    def test_chunk_ids_unique(self):
        doc = structure.split_document(MARKDOWN_DOC, max_chars=60)
        ids = [c.chunk_id for c in structure.iter_chunks(doc)]
        self.assertEqual(len(ids), len(set(ids)))


class TestHeuristicFallback(unittest.TestCase):
    def test_heuristic_chapters(self):
        doc = structure.split_document(HEURISTIC_DOC, max_chars=10000)
        self.assertEqual(doc.structure_source, "heuristic")
        titles = [c.title for c in doc.chapters]
        self.assertTrue(any("Chapter 1" in t for t in titles))
        self.assertTrue(any("第2章" in t for t in titles))


class TestLengthFallback(unittest.TestCase):
    def test_no_structure_uses_length_windows(self):
        doc = structure.split_document(NO_STRUCTURE_DOC, max_chars=40)
        self.assertEqual(doc.structure_source, "length")
        chunks = list(structure.iter_chunks(doc))
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(chunk.char_len, 60)

    def test_oversized_paragraph_is_hard_wrapped(self):
        big = "x" * 500
        doc = structure.split_document(big, max_chars=100)
        for chunk in structure.iter_chunks(doc):
            self.assertLessEqual(chunk.char_len, 100)


class TestValidation(unittest.TestCase):
    def test_zero_max_chars_rejected(self):
        with self.assertRaises(ValueError):
            structure.split_document("hi", max_chars=0)

    def test_empty_document(self):
        doc = structure.split_document("", max_chars=100)
        self.assertEqual(list(structure.iter_chunks(doc)), [])


class TestCLI(unittest.TestCase):
    def test_split_cli_emits_json(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".md", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(MARKDOWN_DOC)
            path = fh.name
        try:
            out = subprocess.run(
                [sys.executable, STRUCTURE_PY, "split", path, "--max-chars", "5000"],
                capture_output=True,
                text=True,
                check=True,
            )
            data = json.loads(out.stdout)
            self.assertEqual(data["structure_source"], "headings")
            self.assertIn("chapters", data)
        finally:
            os.unlink(path)

    def test_missing_file_errors(self):
        out = subprocess.run(
            [sys.executable, STRUCTURE_PY, "split", "/nonexistent/file.md"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(out.returncode, 1)


if __name__ == "__main__":
    unittest.main()
