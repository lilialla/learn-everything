# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); this project is pre-1.0 and versions are
informal during alpha.

## [Unreleased]

- Community health files (CONTRIBUTING, SECURITY, issue/PR templates), bilingual README, CI.

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
- **Tests.** 44 unit tests for the engine + a from-zero end-to-end acceptance run.

### Notes
- Privacy-first: learner data (`tracks/`, `profile.md`, `registry.json`, `.obsidian/`, `.claudian/`)
  is gitignored and never leaves the machine.
- Deferred/frozen backlog: exam & applied modes, URL / long-document ingestion, MCP server,
  personalized FSRS weights — see `plans/specs/2026-06-22-feature-designs.md`.

[Unreleased]: https://github.com/lilialla/learn-everything/compare/main...HEAD
