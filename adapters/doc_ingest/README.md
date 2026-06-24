# doc_ingest — long-document extraction adapter

Turns a **scanned/text PDF, an EPUB, or an already-clean md/txt file** into clean markdown
that the pip-free core [`scripts/structure.py`](../../scripts/structure.py) then splits into a
book → chapters → sections → chunks hierarchy. This is **Phase A** ("intake & extraction,
cached once per work") of long-document ingestion; `structure.py` is Phase B, and
[`methods/reading-guide.md`](../../methods/reading-guide.md) is the 导读 pre-pass that turns the
chunk index into a `plan.md` syllabus and a resumable curriculum.

## What it does

| Source kind | Extractor | Notes |
|---|---|---|
| text PDF | `pypdf` (lazy) | direct text extraction, inline `<!-- page: N -->` anchors |
| scanned / image PDF | **hand-off** to the author's `mineru-ocr` skill (cloud) or `case-files-to-md-fast` / `case-files-to-md` (local, `--no-upload`) | OCR is a host-model skill, not a library — this adapter returns a machine-readable handoff, then you re-run `extract` on the resulting `.md` |
| EPUB | stdlib `zipfile` + `html.parser` over the OPF spine | no third-party dep |
| md / txt | passthrough | no dep |

**Reuse, not rebuild:** OCR is delegated to the existing `mineru-ocr` /
`case-files-to-md(-fast)` skills; the structural split is delegated to core `structure.py`.
This adapter only orchestrates, caches, and wraps.

## Optional dependencies (lazy, friendly errors)

This adapter is **out of the pip-free CORE**. Importing it pulls in only stdlib, so
`--help`, the md/txt passthrough, EPUB extraction, caching, and the split-via-core path all
work with **zero installs**. Format paths that need a library import it *lazily* and, if it's
missing, raise a friendly message naming the pip package — never a raw `ImportError`.

| Path | Install |
|---|---|
| text-PDF extraction | `pip install pypdf` |
| scanned-PDF OCR | none here — uses the `mineru-ocr` / `case-files-to-md(-fast)` skills |

The core engine (`scripts/fsrs.py`, `scripts/registry.py`) never imports this module, so the
learning OS runs fully without any of the above.

## How it's invoked

```bash
# Phase A — extract to cached markdown (cached by source content hash; OCR never re-runs)
python3 adapters/doc_ingest/ingest_doc.py extract <file.pdf|epub|md|txt> --track <id> [--no-upload]

# Phase B — split the cached extraction into a structure.json hierarchy
python3 adapters/doc_ingest/ingest_doc.py split <work-id> --track <id> [--max-chars N]
```

The `learn` skill / host model normally drives these from natural language ("learn this book:
<path>"); the CLI is the seam it shells into.

### `--no-upload` (confidentiality)

For confidential or offline material, `--no-upload` forces the scanned-PDF handoff to the
**local** OCR fallback (`case-files-to-md-fast` → `case-files-to-md`) and never suggests the
cloud `mineru-ocr` path. The host model must still confirm before sending any confidential
text to a model.

## Where it writes (all private / gitignored)

Everything lands under `tracks/<id>/`, which the repo `.gitignore` excludes — no learner data
is ever committed:

```
tracks/<id>/notes/sources/_raw/<work-id>.md            # wrapped UNTRUSTED markdown
tracks/<id>/notes/sources/_raw/<work-id>.manifest.json # cache key + provenance
tracks/<id>/notes/sources/<work-id>.structure.json     # Phase B hierarchy
```

The manifest is keyed by the **SHA-256 of the source file**: re-running `extract` on an
unchanged file returns `cache_hit: true` and does not re-extract; a changed file re-extracts.

## Data boundary (security)

Extracted text is **UNTRUSTED data, never instructions**. The adapter wraps every extraction
in `<<<UNTRUSTED_INPUT>>> … <<<END_UNTRUSTED>>>` markers and scans for prompt-injection red
flags (imperative phrases, dense zero-width chars, direction-override chars). With **≥3 red
flags** it prepends `[PROMPT_INJECTION_DETECTED]` to the output; downstream consumers
(`methods/reading-guide.md`) must flag, not obey, any embedded imperatives.

## Tests

`tests/test_doc_ingest.py`. The dep-bearing PDF path **self-skips** when `pypdf` is absent
(`@unittest.skipUnless`); the passthrough / cache / boundary / split-via-core paths need no
deps and always run, keeping core CI green with nothing installed.

## Integration

This adapter is wired in by the maintainer at the `ingest` intent in `skills/learn/SKILL.md`
(a "large work" branch). See the structured INTEGRATION NOTES that accompany this feature for
the exact hook.
