# providers/ — vendored fetchers (clone-and-go)

These are **bundled into the repo on purpose** so a fresh clone can turn a
video/article link into a learning track with no extra download. The
`adapters/url_ingest` routes shell out to them; you don't call them directly.

| dir | what it fetches | stack | runtime deps (NOT bundled) | license |
|-----|-----------------|-------|----------------------------|---------|
| `video-notes/` | B站 / YouTube / 抖音 subtitles → text (audio→FunASR fallback) | Python | `yt-dlp` (`pip install yt-dlp`); YouTube/抖音 want a logged-in browser (`--browser edge`) | personal-study use — see its `SKILL.md` |
| `wechat-article-fetch/` | 微信公众号 (mp.weixin) article → markdown | Node + Playwright | Node.js + `npm install` here (pulls Playwright, ~hundreds of MB) | MIT © 2025 杨卫薪律师（微信ywxlaw） — see `LICENSE.txt` |

## Important: vendored = source, not the heavy deps

Copying the code in does **not** remove its runtime requirements. Each provider
still needs its own tools installed before it can actually fetch:

```bash
# video provider
pip install yt-dlp

# wechat provider (Playwright is huge → installed on demand, git-ignored)
cd providers/wechat-article-fetch && npm install
```

Until those are present, the route raises a friendly `IngestError` telling you
exactly what to install. The deterministic CORE (`scripts/`) stays pip-free and
never imports any of this.

## How they're found

`adapters/url_ingest/ingest.py:_find_provider` resolves, in order:

1. an env var override — `$LEARN_VIDEO_NOTES` / `$LEARN_WECHAT_FETCH`
   (point at a custom `fetch_subtitles.py` / `fetch.js`);
2. **these vendored copies** (the default — works on a bare clone);
3. an existing skill under `~/.claude` (so an installed copy is reused).

## Attribution & licensing

- **wechat-article-fetch** is third-party MIT. Its `LICENSE.txt` (copyright
  notice + permission text) is retained verbatim, as MIT requires. Not modified.
- **video-notes** is bundled with its original `SKILL.md`/`README.md`, which
  state it is **for personal study use** and explicitly *not* for bulk scraping
  or redistribution of account data. That usage note travels with the code —
  please honor it. Use it to learn from links you're entitled to read.

Both providers are unmodified copies. To update one, re-copy from its source and
keep its license/usage notes intact.
