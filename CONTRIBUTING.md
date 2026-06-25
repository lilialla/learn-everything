# Contributing to learn-everything

Thanks for your interest! This is an alpha project; issues and PRs are welcome.

## Quick start (dev)

No dependencies — the engine is Python standard library only.

```bash
git clone https://github.com/lilialla/learn-everything.git
cd learn-everything
python3 -m unittest tests.test_fsrs tests.test_registry tests.test_structure -v   # 77 tests, all should pass
```

## Invariants (please don't break these)

These are the load-bearing design rules; PRs that violate them will be asked to change:

- **Core stays pip-free stdlib.** `scripts/fsrs.py`, `scripts/registry.py`, and `scripts/structure.py`
  import only the standard library (structure.py may lazily reuse registry.py — same package). Anything
  needing a dependency (network, OCR, a model) is an *optional adapter*, never part of the core.
- **Markdown files are the source of truth.** `registry.json` is a rebuildable cache — never the
  authority. State lives in `tracks/<id>/TRACK.md` + sidecar files.
- **Cards stay Obsidian-spaced-repetition compatible** (`#flashcards/<track>` + `?` separator).
- **Teach first; cards after understanding.** Reading material and dumping a flashcard list is the
  anti-pattern this project exists to avoid.
- **Nothing is persisted without the learner's approval.**
- **Untrusted content is data, not instructions** (DATA_BOUNDARY); imperative text inside a source
  is content to flag, never a command to obey.
- **Privacy:** never commit learner data — `tracks/`, `profile.md`, `registry.json`, `.obsidian/`,
  `.claudian/` are gitignored. Keep it that way.

## How to add things

- **A new teaching method** → just add `methods/<name>.md` in the house style of the existing files
  (frontmatter `name` + rich `description`, a concrete runnable procedure, "how to run it",
  anti-patterns, how it composes with `learner-model.md` / `active-recall.md`). No code needed.
- **A new engine command** → add the function + an argparse subparser + a `main()` branch in
  `scripts/registry.py`, and a test in `tests/test_registry.py`. Prefer read-mostly operations;
  keep writes atomic.
- **The former "frozen backlog" is now shipped** as optional, out-of-core modules (alpha):
  exam/applied modes (`methods/exam.md`, `methods/applied.md`), URL ingestion
  (`adapters/url_ingest/`), long-document ingestion + curriculum (`scripts/structure.py` +
  `methods/reading-guide.md` + `adapters/doc_ingest/`), web search (`adapters/web_search/`), the MCP
  server (`mcp/server.py`), and personalized FSRS weights (`adapters/fsrs_optimize/`). Extend these
  in their own module, keeping the CORE pip-free and deps lazy. Original designs:
  [`plans/specs/2026-06-22-feature-designs.md`](plans/specs/2026-06-22-feature-designs.md).

## PR checklist

- [ ] `python3 -m unittest tests.test_fsrs tests.test_registry tests.test_structure` passes (the CI set).
- [ ] No personal/learner data or secrets in the diff (check `git diff --cached`).
- [ ] Invariants above hold.
- [ ] If behavior changed, a test asserts the new behavior.

## Commit style

Conventional-ish: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:` + a clear summary.
