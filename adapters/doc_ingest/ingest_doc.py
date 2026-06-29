#!/usr/bin/env python3
"""Long-document extraction adapter (OPTIONAL — out of the pip-free CORE).

Turns a scanned/text PDF, an EPUB, or an already-clean md/txt file into clean
markdown that scripts/structure.py can then split into a learning curriculum.

This is Phase A ("intake & extraction, cached once per work") of the
long-document ingestion design. It deliberately REUSES rather than rebuilds:

  - scanned / image PDF  -> the author's `mineru-ocr` skill (structured md with
    page anchors), with `case-files-to-md-fast` / `case-files-to-md` as the
    local, no-upload fallback for confidential or offline material.
  - text PDF             -> `pypdf` (pure-python text extraction).
  - EPUB                 -> stdlib `zipfile` + `xml`/`html.parser` over the
    XHTML spine (no third-party dep needed).
  - md / txt             -> passthrough.

CORE INVARIANT: this module is NEVER imported by scripts/fsrs.py or
scripts/registry.py. All dep-bearing imports (pypdf, mineru, …) are LAZY and
local to the function that needs them, each raising a friendly message naming
the pip package to install — never a raw ImportError at import time. Importing
THIS module pulls in only stdlib, so `python3 adapters/doc_ingest/ingest_doc.py
--help` works with zero installs and only fails (helpfully) when you actually
ask it to extract a format whose library is missing.

Output of extraction is markdown wrapped as UNTRUSTED data (DATA_BOUNDARY): the
caller (the reading-guide pre-pass / the learn skill) must treat the extracted
text as content to map, never as instructions.

CLI:
    python3 ingest_doc.py extract <file> --track <id> [--no-upload]
    python3 ingest_doc.py split   <work-id> --track <id> [--max-chars N]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths. Learner data is private: everything is written under tracks/<id>/,
# which the repo .gitignore excludes. Nothing here writes to tracked files.
# ---------------------------------------------------------------------------

# adapters/doc_ingest/ingest_doc.py -> repo root is two parents up.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from adapters.safety import (  # noqa: E402
    UNTRUSTED_CLOSE,
    UNTRUSTED_OPEN,
    wrap_untrusted_text,
)

# Sample this many bytes per page-equivalent when sniffing text vs scanned PDF.
SCANNED_PDF_CHARS_PER_PAGE = 100  # below this avg => probably scanned/image


def repo_root() -> Path:
    return REPO_ROOT


def track_dir(track: str, root: Path | None = None) -> Path:
    scripts = repo_root() / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import registry  # type: ignore  # noqa: PLC0415

    return registry.track_dir(track, root or repo_root())


def sources_dir(track: str, root: Path | None = None) -> Path:
    return track_dir(track, root) / "notes" / "sources"


def raw_dir(track: str, root: Path | None = None) -> Path:
    return sources_dir(track, root) / "_raw"


# ---------------------------------------------------------------------------
# Friendly lazy-import helper
# ---------------------------------------------------------------------------


def _require(module: str, pip_name: str):
    """Import `module` lazily, or raise a friendly RuntimeError naming the pip
    package — never a bare ImportError, never at module import time."""
    try:
        return __import__(module)
    except ImportError as exc:  # pragma: no cover - exercised only without dep
        raise RuntimeError(
            f"this step needs the optional '{pip_name}' package, which is not "
            f"installed.\n  install it with:  pip install {pip_name}\n"
            f"(this adapter is out-of-core; the pip-free learning engine does "
            f"not need it.)"
        ) from exc


# ---------------------------------------------------------------------------
# Source kind detection
# ---------------------------------------------------------------------------


def detect_kind(path: Path) -> str:
    """Return 'pdf_text' | 'pdf_scanned' | 'epub' | 'markdown' | 'text'.

    PDF text-vs-scanned is sniffed by sampling extractable chars per page; if
    pypdf is unavailable we conservatively report 'pdf_scanned' so the caller
    routes to OCR (mineru / local fallback) rather than failing.
    """
    suffix = path.suffix.lower()
    if suffix in (".md", ".markdown"):
        return "markdown"
    if suffix in (".txt", ".text"):
        return "text"
    if suffix == ".epub":
        return "epub"
    if suffix == ".pdf":
        return _sniff_pdf(path)
    # Unknown extension: treat as plain text and let extraction decide.
    return "text"


def _sniff_pdf(path: Path) -> str:
    try:
        pypdf = _require("pypdf", "pypdf")
    except RuntimeError:
        # No pypdf -> assume scanned so we hand off to OCR (which the author's
        # mineru-ocr skill handles), instead of crashing on a sniff.
        return "pdf_scanned"
    try:
        reader = pypdf.PdfReader(str(path))
        pages = reader.pages
    except Exception:  # noqa: BLE001 - malformed/unreadable PDF -> route to OCR
        return "pdf_scanned"
    sample = pages[: min(5, len(pages))]
    total = 0
    for pg in sample:
        try:
            total += len(pg.extract_text() or "")
        except Exception:  # noqa: BLE001 - malformed page should not crash sniff
            pass
    avg = total / max(1, len(sample))
    return "pdf_text" if avg >= SCANNED_PDF_CHARS_PER_PAGE else "pdf_scanned"


# ---------------------------------------------------------------------------
# Extractors (lazy deps; pure-stdlib where possible)
# ---------------------------------------------------------------------------


def _extract_pdf_text(path: Path) -> str:
    pypdf = _require("pypdf", "pypdf")
    reader = pypdf.PdfReader(str(path))
    parts: list[str] = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            txt = page.extract_text() or ""
        except Exception:  # noqa: BLE001
            txt = ""
        # Leave an inline page anchor structure.py understands.
        parts.append(f"<!-- page: {i} -->\n{txt.strip()}\n")
    return "\n".join(parts).strip() + "\n"


class _EpubTextExtractor(HTMLParser):
    """Minimal XHTML -> text/markdown-ish extractor (stdlib only)."""

    BLOCK_TAGS = {"p", "div", "br", "li", "section", "article"}
    HEADING_TAGS = {"h1": "# ", "h2": "## ", "h3": "### ", "h4": "#### "}

    def __init__(self) -> None:
        super().__init__()
        self._out: list[str] = []
        self._pending_heading: str | None = None
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip_depth += 1
            return
        if tag in self.HEADING_TAGS:
            self._out.append("\n\n" + self.HEADING_TAGS[tag])
            self._pending_heading = tag
        elif tag in self.BLOCK_TAGS:
            self._out.append("\n\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == self._pending_heading:
            self._pending_heading = None

    def handle_data(self, data):
        if self._skip_depth > 0:
            return
        text = data.strip()
        if text:
            self._out.append(text + " ")

    def get_text(self) -> str:
        joined = "".join(self._out)
        # Collapse runaway blank lines.
        lines = [ln.rstrip() for ln in joined.splitlines()]
        cleaned: list[str] = []
        blank = 0
        for ln in lines:
            if ln == "":
                blank += 1
                if blank <= 1:
                    cleaned.append(ln)
            else:
                blank = 0
                cleaned.append(ln)
        return "\n".join(cleaned).strip() + "\n"


def _extract_epub(path: Path) -> str:
    """Unzip the EPUB, walk its spine in order, convert XHTML -> markdown-ish.

    Pure stdlib (zipfile + html.parser + xml for the OPF spine order).
    """
    import xml.etree.ElementTree as ET

    parts: list[str] = []
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        # Find the OPF (content.opf) to read spine order; fall back to file order.
        opf_name = next(
            (n for n in names if n.lower().endswith(".opf")), None
        )
        spine_files: list[str] = []
        if opf_name is not None:
            try:
                opf = ET.fromstring(zf.read(opf_name))
                ns = {"opf": "http://www.idpf.org/2007/opf"}
                base = opf_name.rsplit("/", 1)[0] if "/" in opf_name else ""
                manifest = {}
                for item in opf.iter():
                    if item.tag.endswith("}item") or item.tag == "item":
                        iid = item.get("id")
                        href = item.get("href")
                        if iid and href:
                            manifest[iid] = href
                for ref in opf.iter():
                    if ref.tag.endswith("}itemref") or ref.tag == "itemref":
                        idref = ref.get("idref")
                        if idref and idref in manifest:
                            href = manifest[idref]
                            full = f"{base}/{href}" if base else href
                            spine_files.append(full)
            except ET.ParseError:
                spine_files = []
        if not spine_files:
            spine_files = [
                n for n in names if n.lower().endswith((".xhtml", ".html", ".htm"))
            ]
        for fname in spine_files:
            try:
                raw = zf.read(fname).decode("utf-8", errors="replace")
            except KeyError:
                continue
            parser = _EpubTextExtractor()
            parser.feed(raw)
            chunk = parser.get_text()
            if chunk.strip():
                parts.append(chunk)
    return ("\n\n".join(parts)).strip() + "\n"


def _ocr_handoff_message(path: Path, no_upload: bool) -> str:
    """Build the instruction for routing a scanned PDF to the author's OCR skills.

    We do NOT shell into the skills here (they are host-model skills, not
    libraries); instead we return a clear, machine-readable handoff the learn
    skill / host model executes. This keeps reuse honest: the OCR work is done
    by mineru-ocr / case-files-to-md(-fast), not reimplemented.
    """
    if no_upload:
        primary = "case-files-to-md-fast (local, no upload)"
        fallback = "case-files-to-md (local, higher precision)"
    else:
        primary = "mineru-ocr (structured md, page anchors)"
        fallback = "case-files-to-md-fast (local fallback if MinerU unavailable)"
    return (
        f"SCANNED_PDF_NEEDS_OCR: {path.name}\n"
        f"  This is a scanned/image PDF. Extraction is a host-model skill, not a\n"
        f"  library call. Route it through:\n"
        f"    primary : {primary}\n"
        f"    fallback: {fallback}\n"
        f"  Then re-run:  ingest_doc.py extract <the-resulting.md> --track <id>\n"
        f"  (Confidential material: use the local --no-upload path.)"
    )


# ---------------------------------------------------------------------------
# DATA_BOUNDARY wrapping + injection scan
# ---------------------------------------------------------------------------

def wrap_untrusted(text: str) -> tuple[str, list[str]]:
    """Wrap extracted text in DATA_BOUNDARY markers; prepend an injection
    warning header when >=3 red flags are present. Returns (wrapped, flags)."""
    return wrap_untrusted_text(text, include_flag_details=True)


# ---------------------------------------------------------------------------
# Extraction orchestration (Phase A) — cached by source content hash
# ---------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def _work_id(path: Path, digest: str) -> str:
    return f"{_slug(path.stem)}-{digest[:8]}"


def _slug(name: str) -> str:
    keep = [c if (c.isalnum() or c in "-_") else "-" for c in name.lower()]
    out = "".join(keep).strip("-")
    while "--" in out:
        out = out.replace("--", "-")
    return out or "work"


def extract(
    file: str,
    track: str,
    no_upload: bool = False,
    root: Path | None = None,
    extractor_fn=None,
) -> dict:
    """Phase A: extract `file` to clean markdown, cached by content hash.

    Writes (under the gitignored tracks/<id>/notes/sources/_raw/):
      - <work-id>.md            the wrapped, UNTRUSTED markdown
      - <work-id>.manifest.json the cache key + provenance

    On a hash match, returns the cached manifest WITHOUT re-extracting
    (`cache_hit: true`) — OCR/extraction never re-runs for the same file.

    `extractor_fn` is an injection seam for tests (call-count assertions); when
    None the real format extractors are used.
    """
    path = Path(file)
    if not path.is_file():
        raise FileNotFoundError(f"not a file: {path}")

    digest = _sha256(path)
    work_id = _work_id(path, digest)
    rd = raw_dir(track, root)
    manifest_path = rd / f"{work_id}.manifest.json"
    md_path = rd / f"{work_id}.md"

    if manifest_path.is_file() and md_path.is_file():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("sha256") == digest:
            existing["cache_hit"] = True
            return existing

    kind = detect_kind(path)

    if extractor_fn is not None:
        text = extractor_fn(path, kind)
    elif kind == "pdf_text":
        text = _extract_pdf_text(path)
    elif kind == "pdf_scanned":
        # We cannot do OCR in-library; return a handoff manifest, write nothing.
        return {
            "work_id": work_id,
            "sha256": digest,
            "kind": kind,
            "cache_hit": False,
            "needs_ocr": True,
            "handoff": _ocr_handoff_message(path, no_upload),
        }
    elif kind == "epub":
        text = _extract_epub(path)
    else:  # markdown / text passthrough
        text = path.read_text(encoding="utf-8", errors="replace")

    wrapped, flags = wrap_untrusted(text)

    rd.mkdir(parents=True, exist_ok=True)
    md_path.write_text(wrapped, encoding="utf-8")

    manifest = {
        "work_id": work_id,
        "source_path": str(path),
        "sha256": digest,
        "kind": kind,
        "chars": len(text),
        "est_tokens": int(len(text) / 3.5),
        "extractor": kind,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "raw_md": str(md_path),
        "injection_flags": flags,
        "cache_hit": False,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def split(work_id: str, track: str, max_chars: int | None = None,
          root: Path | None = None) -> dict:
    """Phase B: split a cached extraction into a structure.json hierarchy.

    Delegates the actual splitting to the pip-free core scripts/structure.py
    (reuse-not-rebuild). Writes notes/sources/<work-id>.structure.json.
    """
    # Import the core splitter lazily so importing this adapter never depends on
    # sys.path being set up; structure.py itself is pip-free.
    structure = _load_structure()

    rd = raw_dir(track, root)
    md_path = rd / f"{work_id}.md"
    if not md_path.is_file():
        raise FileNotFoundError(
            f"no cached extraction for work-id {work_id!r}; run 'extract' first"
        )
    text = md_path.read_text(encoding="utf-8")
    kwargs = {} if max_chars is None else {"max_chars": max_chars}
    doc = structure.split_document(text, title=work_id, **kwargs)
    out = structure.to_dict(doc)

    structure_path = sources_dir(track, root) / f"{work_id}.structure.json"
    structure_path.parent.mkdir(parents=True, exist_ok=True)
    structure_path.write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {
        "work_id": work_id,
        "structure_path": str(structure_path),
        "structure_source": out["structure_source"],
        "n_chapters": len(out["chapters"]),
        "n_chunks": sum(
            len(s["chunks"]) for c in out["chapters"] for s in c["sections"]
        ),
    }


def _load_structure():
    """Import scripts/structure.py (pip-free core) from the repo."""
    scripts = repo_root() / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import structure  # noqa: PLC0415

    return structure


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="long-document extraction adapter (optional, out-of-core)"
    )
    sub = p.add_subparsers(dest="command", required=True)

    e = sub.add_parser("extract", help="extract a file to cached markdown (Phase A)")
    e.add_argument("file", help="path to PDF / EPUB / md / txt")
    e.add_argument("--track", required=True, help="track id (output goes under tracks/<id>/)")
    e.add_argument(
        "--no-upload",
        action="store_true",
        help="confidential/offline: force the local OCR fallback, never cloud",
    )

    s = sub.add_parser("split", help="split a cached extraction into structure.json (Phase B)")
    s.add_argument("work_id", help="work id from a prior extract")
    s.add_argument("--track", required=True, help="track id")
    s.add_argument("--max-chars", type=int, default=None, help="max chars per chunk")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "extract":
            result = extract(args.file, args.track, no_upload=args.no_upload)
        elif args.command == "split":
            result = split(args.work_id, args.track, max_chars=args.max_chars)
        else:  # pragma: no cover - argparse enforces choices
            print(f"unknown command: {args.command}", file=sys.stderr)
            return 2
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:  # friendly missing-dep message
        print(f"error: {exc}", file=sys.stderr)
        return 1
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
