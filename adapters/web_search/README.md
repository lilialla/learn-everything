# web_search — optional, out-of-CORE web search

Lets the `learn` skill **fill a gap** or **verify a claim** while teaching —
without leaving the loop. It is glue, not a scraper: it runs ONE query and hands
back ranked results as **UNTRUSTED DATA** for the host model to read, weigh, and
**cite** — never to obey. It writes nothing to a track.

The deterministic CORE (`scripts/`) stays pip-free: the backend is resolved
lazily, so importing this adapter needs no install.

## When the skill uses it

- A learner asks something the current source doesn't cover → search, then teach
  from what's found (citing the link).
- A claim in the material (or in the dialogue) needs checking → search to verify;
  surface agreement/conflict rather than asserting.
- A prerequisite is missing → find a short explainer to bridge it.

It is **opt-in per moment**, not automatic — the tutor decides a search is worth
it, tells the learner, and treats every result as a source to evaluate.

## Contract

```python
from adapters.web_search import search, format_results_md, readiness, WebSearchError
r = search("FSRS spaced repetition algorithm", max_results=5)
# -> {query, backend, count, results:[{title,url,snippet,injection_flagged}],
#     untrusted: True, injection_flagged}
md = format_results_md(r)   # DATA_BOUNDARY-wrapped markdown, ready to read
```
`search` raises `WebSearchError(reason, query)` on an empty query or no backend —
never a half-result.

## CLI

```bash
python3 adapters/web_search/search.py --check                 # backend ready?
python3 adapters/web_search/search.py --query "..." [--max 5] [--md]
```

## Backend resolution (lazy)

1. **`$LEARN_WEB_SEARCH`** — a command run as `<cmd> "<query>" <max>` that prints
   a JSON array (or `{"results": [...]}`) of `{title,url,snippet}`. Plug in any
   engine / API / your own script (e.g. a Brave/Bing/SerpAPI wrapper) this way.
2. else the **`ddgs`** package (maintained DuckDuckGo search), or the older
   `duckduckgo_search`.
3. else a friendly `WebSearchError` telling you to set the env var or
   `pip install ddgs`.

Field aliases are normalized (`href`/`link` → `url`, `body`/`description` →
`snippet`), so most backends' raw rows work as-is.

## Safety — results are untrusted

Every result's title+snippet is injection-scanned; `injection_flagged` is set per
result and overall, and `format_results_md` prepends `[PROMPT_INJECTION_DETECTED]`
when triggered. The body is wrapped in `<<<UNTRUSTED_INPUT>>> … <<<END_UNTRUSTED>>>`
— the same DATA_BOUNDARY the rest of the project uses. Imperative text inside a
result is content to flag, never a command to obey.

## Tests

```bash
python3 -m unittest adapters.web_search.test_search   # stdlib only, fake backend, no network
```
