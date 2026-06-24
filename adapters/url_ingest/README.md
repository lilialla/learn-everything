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

| route  | needs | notes |
|--------|-------|-------|
| web    | `requests`, `beautifulsoup4` (+ optional `readability-lxml`) | direct main-content extraction |
| video  | the **video-notes** skill (Python + `yt-dlp`) | **delegated** — B站/YouTube/抖音 subtitles, FunASR audio fallback |
| wechat | the **wechat-article-fetch** skill (Node + Playwright, MIT) | **delegated** — runs `node fetch.js` |
| pdf    | `requests` | OCR delegated to `mineru-ocr` / `case-files-to-md-fast` (local, no upload) |

`prefer_local=True` forces no-upload PDF routes for confidential tracks.

## Providers — reuse existing skills, don't re-scrape (video / wechat)

The `video` and `wechat` routes **delegate to proven local skills** rather than
re-implementing scraping (reuse-not-rebuild; those skills handle login state,
anti-bot, `--browser edge`, image filtering, etc.). The adapter finds them by:

1. an explicit env var — **`LEARN_VIDEO_NOTES`** → a `video-notes`
   `fetch_subtitles.py`; **`LEARN_WECHAT_FETCH`** → a `wechat-article-fetch`
   `fetch.js` (set these for any clone / CI / a custom location);
2. else auto-probe `~/.claude` (`.claude/plugins/*/skills/<name>/…` and
   `.claude/skills/<name>/…`) — so an existing install is found automatically.

If no provider is found, the route raises a friendly `IngestError` telling the
user to set the env var, install the skill, or run it manually and paste the
result. (These skills are **not vendored** into this repo: `video-notes` is
"personal-use" and unlicensed for redistribution; `wechat-article-fetch` is MIT
but Node+Playwright — delegation keeps a single source of truth and this repo's
Python/zero-dep core clean.)

## How it's invoked

Via `skills/learn/SKILL.md`'s existing `ingest` action: when the input is a
URL, the skill calls `ingest_url(...)` to obtain `source_md_path`, then runs
the normal pasted-text ingest loop on it. No new command, no method-file
changes. If the adapter (or a route's dep) is absent, the skill degrades
gracefully — tell the user to install the dep or paste the text.

## Limits / known gaps

- `video`/`wechat` **delegate** to their provider skills via subprocess (see
  Providers above) and read back the produced markdown; `pdf` raises an explicit
  hand-off to the doc adapter. The `web` route fetches directly. None re-implement
  an existing scraper (reuse-not-rebuild).
- Live routes have unit coverage via a fake provider; they are not yet exercised
  against real B站/YouTube/抖音/公众号 URLs in CI (network + credentials) —
  validate once on real links before relying on them.
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
