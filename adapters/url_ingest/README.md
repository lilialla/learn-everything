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
# first-use preflight (no network): is this link's fetcher installed?
python3 adapters/url_ingest/ingest.py --check --url <u>
# fetch
python3 adapters/url_ingest/ingest.py --url <u> --track <id>
            [--allow-login] [--prefer-local] [--root <path>] [--today YYYY-MM-DD]
```

`--check` reports `ready` / `NOT READY` plus exactly what to install (it powers
the skill's first-use "install the required fetcher" prompt). `readiness(url)` is
the importable form.

## Optional dependencies (lazy-imported, friendly hint if missing)

CORE (`scripts/fsrs.py`, `scripts/registry.py`) stays pip-free — none of these
are imported at package import time; each loads only when its route runs.

| route  | needs | notes |
|--------|-------|-------|
| web    | `requests`, `beautifulsoup4` (+ optional `readability-lxml`) | direct main-content extraction |
| video  | the **video-notes** skill (Python + `yt-dlp`) | **delegated** — B站/YouTube/抖音 subtitles, FunASR audio fallback |
| wechat | the **wechat-article-fetch** skill (Node + Playwright, MIT) | **delegated** — runs `node fetch.js` |
| pdf    | `requests` | not fetched directly — a `.pdf` URL hands off to `adapters/doc_ingest` (download first) |

`prefer_local=True` forces no-upload PDF routes for confidential tracks.

**Video login (the part people hit at runtime):** B站 reads the user's login cookie
from `~/.config/video-notes-cookie.txt`; YouTube/抖音 read cookies from a logged-in
browser. The adapter passes `--browser edge` to the provider for YouTube/抖音 by
default — override with `$LEARN_VIDEO_BROWSER` (e.g. `chrome`, `firefox`). A
no-transcript `IngestError` names which one is missing (cookie file vs browser
login) instead of failing silently.

## Providers — vendored, clone-and-go (video / wechat)

The `video` and `wechat` routes run **proven fetchers bundled in this repo** under
[`providers/`](../../providers/README.md) rather than re-implementing scraping
(reuse-not-rebuild; they handle login state, anti-bot, `--browser edge`, image
filtering, etc.). So a fresh clone works out of the box. The adapter resolves a
provider, in order:

1. an env var override — **`LEARN_VIDEO_NOTES`** → a `video-notes`
   `fetch_subtitles.py`; **`LEARN_WECHAT_FETCH`** → a `wechat-article-fetch`
   `fetch.js` (for a custom location / CI);
2. the **vendored copy** in `providers/` (the default);
3. else auto-probe `~/.claude` — so an installed skill is reused.

Vendoring the *code* doesn't bundle the heavy *runtime deps*: video needs
`pip install yt-dlp`; wechat needs Node.js + `npm install` (Playwright) inside
`providers/wechat-article-fetch/`. Until those are present the route raises a
friendly `IngestError` naming exactly what to install. Licensing/attribution is
preserved — `wechat-article-fetch` ships its MIT `LICENSE.txt` verbatim;
`video-notes` keeps its "personal-study use" note. See
[`providers/README.md`](../../providers/README.md).

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
