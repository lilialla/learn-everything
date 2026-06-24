# url_ingest — URL → markdown ingestion adapter

Optional, **out-of-CORE** adapter. Turn ONE link into a cleaned *source*
`.md` under a track, then the existing `learn` ingest loop takes over
unchanged. Closes the product loop: **link in → learning out.**

It is glue, not a new scraper: each fetch route wraps an existing skill
(`web-crawl-workflow`, `wechat-article-fetch`, `video-notes`, `mineru-ocr`,
`case-files-to-md-fast`). The genuinely new code is only `classify(url)`, the
route dispatcher, the frontmatter/DATA_BOUNDARY normalizer, and the typed
`IngestError` contract.

## What it does

1. `classify(url)` → `web | wechat | video | pdf | unknown` (host/path only, no network).
2. Fetch via the route's primary (public) tool. Login-gated / bot-checked /
   paywalled / empty pages raise `IngestError` (the skill then offers the
   logged-in-browser path) — it **never writes a partial file**.
3. Normalize to one `.md`: YAML frontmatter (`source_url`, `title`,
   `source_type`, `fetcher`, `fetched_at`, `untrusted: true`,
   `injection_flagged`) + the body wrapped in
   `<<<UNTRUSTED_INPUT>>> … <<<END_UNTRUSTED>>>`.
4. Scan the body for prompt injection (≥3 red flags → prepend
   `[PROMPT_INJECTION_DETECTED]`; the body stays DATA, never obeyed).
5. Write exactly **one** file:
   `tracks/<id>/notes/<date>-<slug>-source.md` (matches `skills/learn/SKILL.md`).
   No cards / `review-state.json` / MOC / `TRACK.md` / `registry.json` — those
   are written only by the existing ingest loop, only after human approval.

## Contract

```python
from adapters.url_ingest import ingest_url
result = ingest_url(url, track, root=None, *,
                    allow_login=False, prefer_local=False, today=None)
# -> {"source_md_path": str, "title": str,
#     "metadata": {source_url, source_type, fetcher, fetched_at,
#                  untrusted=True, injection_flagged, fallback_used, truncated}}
```
Raises `IngestError(reason, source_type, url)` on bot-check / paywall / empty /
unsupported / missing optional dependency.

## CLI

```bash
python3 adapters/url_ingest/ingest.py --url <u> --track <id>
            [--allow-login] [--prefer-local] [--root <path>] [--today YYYY-MM-DD]
```

## Optional dependencies (lazy-imported, friendly hint if missing)

CORE (`scripts/fsrs.py`, `scripts/registry.py`) stays pip-free — none of these
are imported at package import time; each loads only when its route runs.

| route  | needs (install) | notes |
|--------|-----------------|-------|
| web    | `requests`, `beautifulsoup4` (+ optional `readability-lxml`) | main-content extraction |
| wechat | `playwright` (+ `playwright install chromium`) | delegates to `wechat-article-fetch` |
| video  | `yt-dlp` | subtitles only; **FunASR audio fallback is out of scope** → run `video-notes` |
| pdf    | `requests` | OCR delegated to `mineru-ocr` / `case-files-to-md-fast` (local, no upload) |

`prefer_local=True` forces no-upload PDF routes for confidential tracks.

## How it's invoked

Via `skills/learn/SKILL.md`'s existing `ingest` action: when the input is a
URL, the skill calls `ingest_url(...)` to obtain `source_md_path`, then runs
the normal pasted-text ingest loop on it. No new command, no method-file
changes. If the adapter (or a route's dep) is absent, the skill degrades
gracefully — tell the user to install the dep or paste the text.

## Limits / known gaps

- `wechat`/`video`/`pdf` currently raise an explicit hand-off `IngestError`
  (delegate to the named skill) rather than re-implementing those scrapers —
  reuse-not-rebuild. The `web` route fetches directly.
- Login-gated/anti-bot content is a documented limit, surfaced loudly (never a
  half-empty file). Large sources set `metadata.truncated=True` for the
  Long-Document Ingestion hand-off.
- Fetched text is **UNTRUSTED DATA**; embedded imperatives are never obeyed.

## Tests

`test_ingest.py` is stdlib-only (no network, no optional deps) and exercises
`classify` dispatch, `slugify`, the injection scanner, frontmatter/
DATA_BOUNDARY normalization, the path convention, and the no-partial-file
guards:

```bash
python3 -m unittest adapters.url_ingest.test_ingest
```
