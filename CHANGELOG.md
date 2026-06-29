# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); this project is pre-1.0 and versions are
informal during alpha.

## [Unreleased]

- **Control-plane drift fixes.** CI now runs full unittest discovery, MCP smoke tests, and the
  repository secret check. Contributor docs and GitHub templates no longer advertise the old frozen
  backlog policy or static test counts.
- **Six-pillar audit follow-through — four substantive gaps closed:**
  - **Memory now actually persists (P0).** A non-skippable close gate
    (`session-check --strict`) requires a card-or-reason + a Log row today + a `next_action` + a
    CONTEXT.md updated today; `context_check` bounds the digest (warns over ~6000 chars) so it can't
    cause context overload. Cards/notes can carry a `source` for full provenance (trace any fact back
    to its note/url/page).
  - **Big books are taught point-by-point.** A curriculum state machine in `scripts/structure.py`
    (`curriculum-build` → `next-chunk` → `mark` → `curriculum-status`, backed by per-track
    `curriculum.json`) walks a whole book one chunk per session, resumable across days.
  - **Review reaches the learner.** `registry.py nudge` prints one plain line of what's due (count +
    urgent deadlines + leeches) for a Daily Note / shell / cron; `leeches` flags cards that keep
    failing (lapses ≥ 3) to re-teach, surfaced on the status board.
  - **Optional web search.** `adapters/web_search/` fills a gap / verifies a claim mid-lesson;
    results return as UNTRUSTED data to weigh and cite (lazy backend, no core dependency).
  - Honesty fixes: method selection is documented as the tutor's heuristic judgment (not an
    algorithmic selector); the toolkit is described as 7 standalone + 3 composable layers + modes;
    `tests.test_structure` added to CI and the current test commands are documented without relying
    on static counts.
- **Docs repositioning.** Reframed the project as a host-agnostic **Skill** that installs into any
  Skill-capable AI assistant (Claude Code, Obsidian via Claudian, and others) — Obsidian + Claudian
  is now presented as one *recommended* setup, not a requirement. Removed comparative/"not a card
  factory"/"not just the material" marketing copy (the product is original; there is no peer or prior
  version to contrast against) in favor of positive statements of what it does. Internal SKILL
  behavioral rules (teach-before-cards) are unchanged. Corrected stale engine test-count references
  across README/README.zh/CHANGELOG/CONTRIBUTING; synced the 中文 roadmap/credits with English.
- Community health files (CONTRIBUTING, SECURITY, issue/PR templates), bilingual README, CI.
- **Unfroze the deferred backlog as out-of-core adapters + modes** (alpha; stdlib core stays
  pip-free, CI green):
  - `exam` and `applied` track modes (`methods/exam.md`, `methods/applied.md`).
  - URL ingestion adapter (`adapters/url_ingest/`): link → cleaned source markdown.
  - Long-document ingestion: `scripts/structure.py` (stdlib splitter), `methods/reading-guide.md`
    (导读 syllabus), `adapters/doc_ingest/` (OCR/extraction).
  - MCP server (`mcp/server.py`) wrapping the core for other hosts.
  - Personalized FSRS weights (`adapters/fsrs_optimize/`) + a `load_weights` hook in
    `scripts/fsrs.py` (per-track `fsrs-weights.json` auto-loaded when present).
  - Dep-bearing routes import-gracefully and aren't yet exercised against live inputs (alpha).
- **url_ingest video/wechat now run vendored fetchers (clone-and-go).** The proven `video-notes`
  (B站/YouTube/抖音 subtitles) and `wechat-article-fetch` (公众号, Node+Playwright) skills are
  **bundled in-repo under `providers/`** so a fresh clone works with no extra download. Resolution
  order: `$LEARN_VIDEO_NOTES`/`$LEARN_WECHAT_FETCH` → vendored copy → `~/.claude`. Source only is
  vendored (no `node_modules`); runtime deps (`yt-dlp`; Node + `npm install` Playwright) install on
  demand and the route raises a friendly hint if they're missing. `wechat-article-fetch`'s MIT
  `LICENSE.txt` is retained verbatim; `video-notes` keeps its personal-study-use note. See
  `providers/README.md`.
- **First-use install preflight for link ingestion.** `adapters/url_ingest/ingest.py --check --url <u>`
  reports (no network) whether a link's fetcher is ready and what to install if not; `readiness(url)`
  exposes the same. `skills/learn` runs it before fetching and, when not ready, tells the user this is
  required product setup (e.g. `pip install yt-dlp`, or Node.js + `npm install` for 微信) before
  proceeding — rather than failing mid-fetch.

## [0.1.0-alpha] — 2026-06-24

First public alpha. The deterministic spine and the teaching loop are built and tested
end-to-end; teaching-dialogue quality depends on the host model and isn't yet battle-tested.

### Added
- **Teaching loop (`learn` skill).** Teach-first dialogic flow: pre-flight gate → diagnose →
  teach concept-by-concept → distil a small card set → approve → persist. The "card factory"
  (dump a flashcard list from a source) is explicitly forbidden.
- **Engine (`scripts/`, Python stdlib only).** FSRS-6 scheduler; per-track state in `TRACK.md`
  with a rebuildable `registry.json` cache; atomic writes; graceful corrupt-state recovery.
- **Cross-track orchestration.** Status board that leads with the due count; `plan-day`
  deterministic ranked + time-boxed daily plan; staleness / resume-pointer / needs-cards signals.
- **Memory & traceability.** Per-track `CONTEXT.md` digest, dated `learning-records/`, `glossary.md`,
  a question heatmap (`log-question` / `questions`), and `progress` (total / graduated / 7-day
  accuracy). Captured misconceptions feed forward into the next session's route.
- **Pedagogy toolkit (`methods/*.md`).** 11 methods: tutor, socratic, feynman, active-recall,
  worked-examples, deliberate-practice, elaboration, dual-coding, metacognition, learner-model,
  learning-science — selected by material × learner × goal.
- **Obsidian-native delivery** via the Claudian plugin; cards compatible with obsidian-spaced-repetition.
- **Tests.** 46 unit tests for the engine + a from-zero end-to-end acceptance run.

### Notes
- Privacy-first: learner data (`tracks/`, `profile.md`, `registry.json`, `.obsidian/`, `.claudian/`)
  is gitignored and never leaves the machine.
- At 0.1.0-alpha, exam & applied modes, URL / long-document ingestion, MCP server, and
  personalized FSRS weights were deferred — see `plans/specs/2026-06-22-feature-designs.md`.
  **(True at 0.1.0-alpha only; the backlog has since been unfrozen and shipped — see [Unreleased].)**

[Unreleased]: https://github.com/lilialla/learn-everything/compare/main...HEAD
