#!/usr/bin/env python3
"""Structural split for long-document ingestion (Python stdlib only).

Splits a large markdown/plain document into a hierarchy
    book -> chapters -> sections -> context-sized chunks
by detecting markdown headings (and a "Contents"/"目录" TOC when present),
falling back to heuristic chapter detection ("Chapter N" / "第N章") and then
to plain length windows when a document has no structure at all.

Every node preserves its heading PATH and the document CHAR OFFSETS of the text
it covers, so a later step (the doc_ingest adapter, the reading-guide pre-pass,
or the curriculum picker) can map any chunk back to the source byte-for-byte.

This module is the pip-free CORE half of long-document ingestion: it does no
network / OCR / pip I/O, so it stays importable and testable with zero installs
and may sit beside scripts/fsrs.py and scripts/registry.py. The dep-bearing
extraction (scanned PDF / EPUB -> markdown) lives in adapters/doc_ingest/, which
produces the markdown this module then splits.

Char offsets are measured in PYTHON str indices over the ORIGINAL text, so
text[node.start:node.end] reproduces the covered span exactly.

CLI:
    python3 scripts/structure.py split <file.md> [--max-chars N]
prints ONE json object: the document hierarchy (book/chapters/sections/chunks).
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Tunable constants. Surfaced here so they are not magic numbers in the code.
# ---------------------------------------------------------------------------

# Default chunk size. The design targets ~6-8k tokens/chunk; at the project's
# rough ~3.5 chars/token estimate that is ~21k-28k chars. We default to the
# lower end so a chunk comfortably fits a teaching context window.
DEFAULT_MAX_CHARS = 24000

# A heading deeper than a chapter (## or more) opens a section. The first
# heading level seen anchors "chapter"; deeper levels nest under it.
CHAPTER_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*$")

# Heuristic chapter markers used only when no markdown headings exist.
# Matches "Chapter 3", "CHAPTER III", "第3章", "第三章", "Part 2", etc. at
# the start of a line.
HEURISTIC_CHAPTER_RE = re.compile(
    r"^[ \t]*(?:"
    r"chapter\s+[\dIVXLCDM]+"          # Chapter 12 / Chapter IV
    r"|part\s+[\dIVXLCDM]+"            # Part 2
    r"|第\s*[0-9一二三四五六七八九十百千]+\s*[章篇回节]"  # 第3章 / 第三篇
    r")\b.*$",
    re.IGNORECASE,
)

# A "Contents" / "目录" line that marks the start of a table-of-contents block.
TOC_HEADING_RE = re.compile(
    r"^#{0,6}[ \t]*(?:contents|table\s+of\s+contents|目\s*录|目錄)[ \t]*$",
    re.IGNORECASE,
)

# A page anchor MinerU / OCR may have left inline, e.g. "[page: 137]" or
# "<!-- page 137 -->" or "{{page:137}}". Best-effort; absent = no anchor.
PAGE_ANCHOR_RE = re.compile(
    r"(?:\[\s*page\s*[:#]?\s*(\d+)\s*\]"
    r"|<!--\s*page\s*[:#]?\s*(\d+)\s*-->"
    r"|\{\{\s*page\s*[:#]?\s*(\d+)\s*\}\})",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Data model. Frozen-ish dataclasses; we build them bottom-up and serialize.
# ---------------------------------------------------------------------------


@dataclass
class Chunk:
    """A context-sized leaf span of the document."""

    chunk_id: str
    title: str
    heading_path: list[str]
    start: int
    end: int
    page_range: str | None = None

    @property
    def char_len(self) -> int:
        return self.end - self.start


@dataclass
class Section:
    title: str
    heading_path: list[str]
    start: int
    end: int
    page_range: str | None = None
    chunks: list[Chunk] = field(default_factory=list)


@dataclass
class Chapter:
    title: str
    heading_path: list[str]
    start: int
    end: int
    page_range: str | None = None
    sections: list[Section] = field(default_factory=list)


@dataclass
class Document:
    title: str
    structure_source: str  # toc | headings | heuristic | length
    char_len: int
    max_chars: int
    chapters: list[Chapter] = field(default_factory=list)


# A flat heading record discovered during the first pass.
@dataclass
class _Heading:
    level: int  # 1 = top (chapter), >1 nests as section
    title: str
    line_start: int  # char offset where the heading line begins
    body_start: int  # char offset where the heading's body text begins


# ---------------------------------------------------------------------------
# Heading / TOC detection
# ---------------------------------------------------------------------------


def _find_markdown_headings(text: str) -> list[_Heading]:
    """Return markdown ATX headings in document order with char offsets.

    A "chapter" is the shallowest heading level present; deeper levels nest as
    sections. We normalize so the shallowest level seen maps to level 1.
    """
    raw: list[_Heading] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        m = CHAPTER_HEADING_RE.match(line.rstrip("\n"))
        if m:
            hashes, title = m.group(1), m.group(2).strip()
            raw.append(
                _Heading(
                    level=len(hashes),
                    title=title,
                    line_start=offset,
                    body_start=offset + len(line),
                )
            )
        offset += len(line)
    if not raw:
        return raw
    # Normalize: shallowest hash-level -> 1.
    shallowest = min(h.level for h in raw)
    for h in raw:
        h.level = h.level - shallowest + 1
    return raw


def _has_toc(text: str) -> bool:
    """True if the document opens with an explicit Contents / 目录 block."""
    # Only look near the top: a real TOC sits in the first part of the doc.
    head = text[: min(len(text), 8000)]
    for line in head.splitlines():
        if TOC_HEADING_RE.match(line.strip()):
            return True
    return False


def _find_heuristic_chapters(text: str) -> list[_Heading]:
    """Find chapter starts by "Chapter N" / "第N章" lines (no markdown headings)."""
    found: list[_Heading] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        if HEURISTIC_CHAPTER_RE.match(line.rstrip("\n")):
            title = line.strip()
            found.append(
                _Heading(
                    level=1,
                    title=title,
                    line_start=offset,
                    body_start=offset,  # heuristic markers ARE part of the body
                )
            )
        offset += len(line)
    return found


def _page_range_for(text: str, start: int, end: int) -> str | None:
    """Best-effort page range 'p.X-Y' from inline page anchors in a span."""
    pages: list[int] = []
    for m in PAGE_ANCHOR_RE.finditer(text, start, end):
        for g in m.groups():
            if g is not None:
                pages.append(int(g))
                break
    if not pages:
        return None
    lo, hi = min(pages), max(pages)
    return f"p.{lo}" if lo == hi else f"p.{lo}-{hi}"


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def split_into_chunks(
    text: str,
    start: int,
    end: int,
    max_chars: int,
    heading_path: list[str],
    title: str,
    chunk_counter: list[int],
) -> list[Chunk]:
    """Split text[start:end] into <= max_chars chunks on paragraph boundaries.

    Pure: appends nothing global except the shared monotonically-increasing
    chunk_counter (a one-element list used as a mutable id source so chunk ids
    are unique and stable across the whole document).
    """
    span = text[start:end]
    if not span.strip():
        return []

    chunks: list[Chunk] = []
    if end - start <= max_chars:
        cuts = [(start, end)]
    else:
        cuts = _paragraph_windows(span, start, max_chars)

    for piece_start, piece_end in cuts:
        if not text[piece_start:piece_end].strip():
            continue
        chunk_counter[0] += 1
        cid = f"chunk-{chunk_counter[0]:04d}"
        chunks.append(
            Chunk(
                chunk_id=cid,
                title=title,
                heading_path=list(heading_path),
                start=piece_start,
                end=piece_end,
                page_range=_page_range_for(text, piece_start, piece_end),
            )
        )
    return chunks


def _paragraph_windows(span: str, base: int, max_chars: int) -> list[tuple[int, int]]:
    """Greedily pack paragraphs into <= max_chars windows; returns abs offsets.

    Paragraphs are split on blank lines. A single paragraph longer than
    max_chars is hard-wrapped at max_chars so no chunk ever overflows (the
    design's "if a single chunk still overflows, re-split it smaller").
    """
    # Split on blank lines but keep absolute offsets by walking the string.
    paras: list[tuple[int, int]] = []
    para_start = 0
    blank_run = False
    i = 0
    n = len(span)
    line_start = 0
    for i, ch in enumerate(span):
        if ch == "\n":
            line = span[line_start:i]
            if line.strip() == "":
                if not blank_run and line_start > para_start:
                    paras.append((para_start, line_start))
                    para_start = i + 1
                blank_run = True
            else:
                blank_run = False
            line_start = i + 1
    if para_start < n:
        paras.append((para_start, n))
    if not paras:
        paras = [(0, n)]

    windows: list[tuple[int, int]] = []
    cur_start: int | None = None
    cur_end = 0
    for p_start, p_end in paras:
        # Hard-wrap an oversized single paragraph.
        if p_end - p_start > max_chars:
            if cur_start is not None:
                windows.append((cur_start, cur_end))
                cur_start = None
            w = p_start
            while w < p_end:
                windows.append((base + w, base + min(w + max_chars, p_end)))
                w += max_chars
            continue
        if cur_start is None:
            cur_start, cur_end = p_start, p_end
        elif p_end - cur_start <= max_chars:
            cur_end = p_end
        else:
            windows.append((base + cur_start, base + cur_end))
            cur_start, cur_end = p_start, p_end
    if cur_start is not None:
        windows.append((base + cur_start, base + cur_end))
    return windows


# ---------------------------------------------------------------------------
# Hierarchy assembly
# ---------------------------------------------------------------------------


def _build_from_headings(
    text: str,
    headings: list[_Heading],
    max_chars: int,
    structure_source: str,
    title: str,
) -> Document:
    """Assemble book -> chapter -> section -> chunk from discovered headings."""
    n = len(text)
    chunk_counter = [0]

    # Compute the end offset of every heading's owned span = up to the next
    # heading of the same-or-shallower level (for chapters) / next heading (sec).
    chapters: list[Chapter] = []

    # Determine chapter boundaries: every level-1 heading starts a chapter.
    level1_idx = [i for i, h in enumerate(headings) if h.level == 1]

    # Preamble before the first chapter (front matter) becomes chapter 0 if
    # it holds real text.
    first_start = headings[level1_idx[0]].line_start if level1_idx else 0
    if not level1_idx:
        # Only deeper headings exist; treat each as its own chapter.
        level1_idx = list(range(len(headings)))
        for h in headings:
            h.level = 1
        first_start = headings[0].line_start

    if text[:first_start].strip():
        pre = Chapter(
            title="(front matter)",
            heading_path=[title, "(front matter)"],
            start=0,
            end=first_start,
            page_range=_page_range_for(text, 0, first_start),
        )
        pre.sections.append(
            _section_with_chunks(
                text, "(front matter)", [title, "(front matter)"],
                0, first_start, max_chars, chunk_counter,
            )
        )
        chapters.append(pre)

    for pos, hidx in enumerate(level1_idx):
        ch_head = headings[hidx]
        ch_end = (
            headings[level1_idx[pos + 1]].line_start
            if pos + 1 < len(level1_idx)
            else n
        )
        ch_path = [title, ch_head.title]
        chapter = Chapter(
            title=ch_head.title,
            heading_path=ch_path,
            start=ch_head.line_start,
            end=ch_end,
            page_range=_page_range_for(text, ch_head.line_start, ch_end),
        )

        # Section headings = headings strictly inside this chapter with level>1.
        inner = [
            h
            for h in headings
            if h.level > 1 and ch_head.body_start <= h.line_start < ch_end
        ]
        if not inner:
            chapter.sections.append(
                _section_with_chunks(
                    text, ch_head.title, ch_path,
                    ch_head.body_start, ch_end, max_chars, chunk_counter,
                )
            )
        else:
            # Text between chapter heading and first section = intro section.
            if text[ch_head.body_start:inner[0].line_start].strip():
                chapter.sections.append(
                    _section_with_chunks(
                        text, "(intro)", ch_path + ["(intro)"],
                        ch_head.body_start, inner[0].line_start,
                        max_chars, chunk_counter,
                    )
                )
            for spos, sh in enumerate(inner):
                s_end = (
                    inner[spos + 1].line_start
                    if spos + 1 < len(inner)
                    else ch_end
                )
                chapter.sections.append(
                    _section_with_chunks(
                        text, sh.title, ch_path + [sh.title],
                        sh.line_start, s_end, max_chars, chunk_counter,
                    )
                )
        chapters.append(chapter)

    return Document(
        title=title,
        structure_source=structure_source,
        char_len=n,
        max_chars=max_chars,
        chapters=chapters,
    )


def _section_with_chunks(
    text: str,
    title: str,
    heading_path: list[str],
    start: int,
    end: int,
    max_chars: int,
    chunk_counter: list[int],
) -> Section:
    section = Section(
        title=title,
        heading_path=list(heading_path),
        start=start,
        end=end,
        page_range=_page_range_for(text, start, end),
    )
    section.chunks = split_into_chunks(
        text, start, end, max_chars, heading_path, title, chunk_counter
    )
    return section


def _build_length_only(text: str, max_chars: int, title: str) -> Document:
    """No structure at all: one synthetic chapter/section of length windows."""
    n = len(text)
    chunk_counter = [0]
    ch_path = [title]
    section = _section_with_chunks(
        text, title, ch_path, 0, n, max_chars, chunk_counter
    )
    chapter = Chapter(
        title=title,
        heading_path=ch_path,
        start=0,
        end=n,
        page_range=_page_range_for(text, 0, n),
        sections=[section],
    )
    return Document(
        title=title,
        structure_source="length",
        char_len=n,
        max_chars=max_chars,
        chapters=[chapter],
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def split_document(
    text: str,
    max_chars: int = DEFAULT_MAX_CHARS,
    title: str = "document",
) -> Document:
    """Split a markdown/plain document into a book/chapter/section/chunk tree.

    Detection priority (matches the design's "prefer real structure"):
      1. markdown ATX headings  -> structure_source = "headings"
         (or "toc" if an explicit Contents/目录 block is also present)
      2. heuristic "Chapter N" / "第N章" lines -> "heuristic"
      3. plain length windows -> "length"

    Pure function: no I/O, no globals. text indices are preserved so
    text[chunk.start:chunk.end] reproduces each chunk verbatim.
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")

    headings = _find_markdown_headings(text)
    if headings:
        source = "toc" if _has_toc(text) else "headings"
        return _build_from_headings(text, headings, max_chars, source, title)

    heuristic = _find_heuristic_chapters(text)
    if heuristic:
        return _build_from_headings(
            text, heuristic, max_chars, "heuristic", title
        )

    return _build_length_only(text, max_chars, title)


def to_dict(doc: Document) -> dict:
    """Serialize a Document to a JSON-ready dict (drops empty page_range nulls
    only at the top; keeps explicit nulls inside for round-trip clarity)."""
    return asdict(doc)


def iter_chunks(doc: Document):
    """Yield every Chunk in document order (handy for callers / tests)."""
    for chapter in doc.chapters:
        for section in chapter.sections:
            for chunk in section.chunks:
                yield chunk


# ---------------------------------------------------------------------------
# Curriculum state machine — teach a big book ONE chunk at a time, across
# sessions. `split` produces the hierarchy; this persists per-track progress so
# the tutor can "pick next chunk -> teach it -> mark taught -> resume next time".
# State lives in tracks/<id>/curriculum.json (a rebuildable plan, not engine
# scheduling state — FSRS still owns review-state.json).
# ---------------------------------------------------------------------------

CURRICULUM_FILE = "curriculum.json"


def _registry():
    """Reuse the registry's track-location + atomic-write helpers (same pip-free
    package dir) so 'where tracks live' has a single source of truth."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import registry  # noqa: PLC0415

    return registry


def _today_iso(today: str | None = None) -> str:
    return today or datetime.date.today().isoformat()


def curriculum_path(track_id: str, root: Path | None = None) -> Path:
    return _registry().track_dir(track_id, root) / CURRICULUM_FILE


def build_curriculum(
    track_id: str,
    file: str,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    title: str | None = None,
    root: Path | None = None,
    force: bool = False,
    today: str | None = None,
) -> dict:
    """Split a long source file into an ordered, teachable curriculum for a track.

    Writes tracks/<id>/curriculum.json: every chunk in document order, each
    `pending`, plus the source path/offsets so `next-chunk` can return the actual
    text to teach. Refuses to clobber existing progress unless force=True.
    """
    reg = _registry()
    tdir = reg.track_dir(track_id, root)
    if not tdir.exists():
        raise ValueError(f"unknown track '{track_id}' (create it first)")
    cpath = curriculum_path(track_id, root)
    if cpath.exists() and not force:
        raise ValueError(
            f"curriculum.json already exists for '{track_id}' — pass force to "
            "rebuild (this RESETS teaching progress)"
        )
    src = Path(file)
    if not src.is_file():
        raise ValueError(f"source file not found: {src}")
    text = src.read_text(encoding="utf-8")
    doc = split_document(text, max_chars=max_chars, title=title or src.stem)
    chunks = [
        {
            "chunk_id": ch.chunk_id,
            "title": ch.title,
            "heading_path": ch.heading_path,
            "page_range": ch.page_range,
            "start": ch.start,
            "end": ch.end,
            "char_len": ch.char_len,
            "status": "pending",
            "taught_on": None,
        }
        for ch in iter_chunks(doc)
    ]
    if not chunks:
        raise ValueError("the source produced no teachable chunks")
    data = {
        "title": doc.title,
        "source_file": str(src),
        "structure_source": doc.structure_source,
        "built": _today_iso(today),
        "max_chars": max_chars,
        "total": len(chunks),
        "position": 0,
        "chunks": chunks,
    }
    reg._atomic_write_text(cpath, json.dumps(data, ensure_ascii=False, indent=2))
    return {
        "track": track_id,
        "total": len(chunks),
        "source_file": str(src),
        "structure_source": doc.structure_source,
        "title": doc.title,
    }


def _load_curriculum(track_id: str, root: Path | None = None) -> tuple[Path, dict]:
    cpath = curriculum_path(track_id, root)
    if not cpath.exists():
        raise ValueError(
            f"no curriculum for '{track_id}' — build one with "
            "`curriculum-build --track <id> <file>`"
        )
    return cpath, json.loads(cpath.read_text(encoding="utf-8"))


def next_chunk(
    track_id: str, *, root: Path | None = None, include_text: bool = True
) -> dict:
    """The next pending chunk to teach (order-gated), with its source text.

    Returns {done: True, ...} when every chunk is taught.
    """
    _cpath, data = _load_curriculum(track_id, root)
    chunks = data["chunks"]
    taught = sum(1 for c in chunks if c["status"] == "taught")
    nxt = next((c for c in chunks if c["status"] != "taught"), None)
    if nxt is None:
        return {
            "done": True, "track": track_id, "total": len(chunks),
            "taught": taught, "remaining": 0,
        }
    out = {
        "done": False,
        "track": track_id,
        "chunk_id": nxt["chunk_id"],
        "title": nxt["title"],
        "heading_path": nxt["heading_path"],
        "page_range": nxt.get("page_range"),
        "total": len(chunks),
        "taught": taught,
        "remaining": len(chunks) - taught,
    }
    if include_text:
        src = Path(data["source_file"])
        if src.is_file():
            out["text"] = src.read_text(encoding="utf-8")[nxt["start"]:nxt["end"]]
        else:
            out["text"] = None
            out["text_error"] = f"source file moved/missing: {src}"
    return out


def mark_chunk(
    track_id: str,
    chunk_id: str,
    status: str = "taught",
    *,
    root: Path | None = None,
    today: str | None = None,
) -> dict:
    """Mark a chunk taught (or back to pending) and advance the position pointer."""
    if status not in ("taught", "pending"):
        raise ValueError("status must be 'taught' or 'pending'")
    cpath, data = _load_curriculum(track_id, root)
    found = False
    for c in data["chunks"]:
        if c["chunk_id"] == chunk_id:
            c["status"] = status
            c["taught_on"] = _today_iso(today) if status == "taught" else None
            found = True
            break
    if not found:
        raise ValueError(f"chunk '{chunk_id}' not in curriculum for '{track_id}'")
    data["position"] = next(
        (i for i, c in enumerate(data["chunks"]) if c["status"] != "taught"),
        len(data["chunks"]),
    )
    _registry()._atomic_write_text(
        cpath, json.dumps(data, ensure_ascii=False, indent=2)
    )
    taught = sum(1 for c in data["chunks"] if c["status"] == "taught")
    return {
        "track": track_id, "chunk_id": chunk_id, "status": status,
        "taught": taught, "total": len(data["chunks"]),
        "remaining": len(data["chunks"]) - taught,
    }


def curriculum_status(track_id: str, root: Path | None = None) -> dict:
    """Progress through a track's curriculum: taught / remaining / next / %."""
    _cpath, data = _load_curriculum(track_id, root)
    chunks = data["chunks"]
    taught = sum(1 for c in chunks if c["status"] == "taught")
    nxt = next((c for c in chunks if c["status"] != "taught"), None)
    total = len(chunks)
    return {
        "track": track_id,
        "title": data.get("title"),
        "source_file": data.get("source_file"),
        "structure_source": data.get("structure_source"),
        "total": total,
        "taught": taught,
        "remaining": total - taught,
        "percent": round(100 * taught / total) if total else 0,
        "done": nxt is None,
        "next_chunk_id": nxt["chunk_id"] if nxt else None,
        "next_title": nxt["title"] if nxt else None,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="structural split for long-document ingestion (stdlib only)"
    )
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("split", help="split a markdown/plain file into a hierarchy")
    sp.add_argument("file", help="path to a .md / .txt / plain file (UTF-8)")
    sp.add_argument(
        "--max-chars",
        type=int,
        default=DEFAULT_MAX_CHARS,
        help=f"max chars per chunk (default {DEFAULT_MAX_CHARS})",
    )
    sp.add_argument(
        "--title",
        default=None,
        help="document title (default: derived from filename)",
    )

    sp = sub.add_parser(
        "curriculum-build",
        help="split a source file into an ordered, teachable curriculum for a track",
    )
    sp.add_argument("file", help="path to the source markdown/text (UTF-8)")
    sp.add_argument("--track", required=True)
    sp.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    sp.add_argument("--title", default=None)
    sp.add_argument("--force", action="store_true", help="rebuild, RESETTING progress")
    sp.add_argument("--today", default=None)

    sp = sub.add_parser(
        "next-chunk", help="the next pending chunk to teach (with its source text)"
    )
    sp.add_argument("--track", required=True)
    sp.add_argument("--no-text", action="store_true", help="omit the chunk text")

    sp = sub.add_parser("mark", help="mark a chunk taught (or back to pending)")
    sp.add_argument("--track", required=True)
    sp.add_argument("--chunk", required=True, help="chunk id, e.g. chunk-0003")
    sp.add_argument("--status", default="taught", choices=["taught", "pending"])
    sp.add_argument("--today", default=None)

    sp = sub.add_parser(
        "curriculum-status", help="progress through a track's curriculum"
    )
    sp.add_argument("--track", required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "split":
        path = Path(args.file)
        if not path.is_file():
            print(f"error: not a file: {path}", file=sys.stderr)
            return 1
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            print(f"error: cannot read {path} ({exc})", file=sys.stderr)
            return 1
        title = args.title or path.stem
        try:
            doc = split_document(text, max_chars=args.max_chars, title=title)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        json.dump(to_dict(doc), sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0

    def _emit(obj) -> int:
        json.dump(obj, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0

    try:
        if args.command == "curriculum-build":
            return _emit(
                build_curriculum(
                    args.track, args.file, max_chars=args.max_chars,
                    title=args.title, force=args.force, today=args.today,
                )
            )
        if args.command == "next-chunk":
            return _emit(next_chunk(args.track, include_text=not args.no_text))
        if args.command == "mark":
            return _emit(
                mark_chunk(args.track, args.chunk, args.status, today=args.today)
            )
        if args.command == "curriculum-status":
            return _emit(curriculum_status(args.track))
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"unknown command: {args.command}", file=sys.stderr)  # pragma: no cover
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
