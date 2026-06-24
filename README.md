# learn-everything

**An AI tutor that teaches you many subjects at once — and remembers.** Talk to it in plain
language inside Obsidian; it teaches one concept at a time, captures what you understood (and
where you stumbled), and quietly schedules spaced reviews so it actually sticks.

`Status: alpha` · `License: MIT` · `Engine: Python stdlib only (zero deps)` · `Tests: 44 passing`

> Most learning tools handle one topic with one method. learn-everything is built for the real
> situation: you're learning five different things at once — a professional domain, an exam, a
> coding skill — each needs a *different* kind of teaching, and you lose the thread every time you
> switch. This keeps the thread.

---

## Why it's different

- **Teach-first, not a card factory.** It teaches you in dialogue (explain → you try → adjust →
  confirm), and only *after* you understand does it distill a few review cards. Reading material
  and dumping a flashcard list is the explicit anti-pattern it refuses.
- **Cross-track orchestration.** Every subject is a "track" under one board. Ask *"what should I do
  today?"* and it answers across all of them at once — what's due to review, what's stale, what's
  near a deadline — and time-boxes a plan.
- **It remembers you, not just the material.** Every session leaves a memory digest, your
  misconceptions, the terms you asked about, and a resume pointer — so days later it reconstructs
  *"here's what you learned, where you got stuck, what's next."*
- **A real pedagogy toolkit.** 11 evidence-based teaching methods (read-along, Socratic, Feynman,
  worked examples, deliberate practice, spaced/active recall, elaboration, dual-coding,
  metacognition, …), chosen automatically to fit the material and the learner.
- **Obsidian-native, one app.** Runs inside Obsidian via the Claudian plugin: read on the left,
  talk to the tutor on the right, notes grow live in your vault. Plain markdown you own.
- **Private by default & zero-dependency.** Your learning data never leaves your machine and is
  gitignored; the engine is pure Python standard library — no `pip install`.

## What you get

- A conversational tutor for any subject, in your language.
- Automatic, durable notes + a per-track "map of content."
- Spaced repetition (FSRS-6) that schedules reviews so knowledge sticks.
- A daily, time-boxed "what to study" plan across every subject.
- Captured misconceptions that **feed forward** — next session re-checks your weak spots and
  corrects the teaching route.
- A question heatmap — see which concepts you asked about most (your weak/important spots).
- Progress you can see: cards learned, cards locked into long-term memory, weekly accuracy.

## Quick start (just talk to it in Obsidian)

The intended way to use learn-everything is **inside Obsidian, in plain language** — you never
touch a command line.

**Day 1 — one-time setup (~10 min):**

1. **Get the files:** `git clone <your-fork-url> learn-everything`.
2. **Open it in Obsidian:** *Open folder as vault* → pick the `learn-everything` folder.
3. **Add the [Claudian](https://github.com/YishenTu/claudian) plugin** (Community plugins →
   search "Claudian" → Install → Enable). It puts an AI tutor in the right sidebar that can read
   and write your vault.
4. **(macOS) If Claudian shows a 401 / auth error:** its bundled Claude needs a credential. Run
   `claude setup-token` in a terminal and paste the token into Claudian's settings as
   `CLAUDE_CODE_OAUTH_TOKEN`. (If you use Claude Code's subscription login, you can instead copy
   your keychain credential to `~/.claude/.credentials.json`.)
5. **(optional) Native review:** add [obsidian-spaced-repetition](https://github.com/st3v3nmw/obsidian-spaced-repetition)
   so the cards the tutor makes are also reviewable inside Obsidian.

**Then just talk to the tutor in the right sidebar** — no commands to remember:

- *"I want to learn &lt;topic&gt;"* / *"teach me this article"* (paste or open it)
- *"pick up where we left off"*
- *"quiz me"* · *"what should I do today?"* · *"how am I doing?"*

It teaches you one concept at a time, writes your notes into the vault as you go, and schedules
reviews so things actually stick.

**Coming back later:** open the vault and ask *"what should I do today?"* — it leads with how many
cards are due across everything. (Want a reminder without opening it? Put this one line in a Daily
Note or a scheduled task to print your due count — no background daemon:
`python3 scripts/registry.py status`.)

## How it works

```
        you talk (plain language)
                 │
   ┌─────────────▼──────────────┐     teach → understand → distill cards → review → resume
   │  learn skill (host adapter) │     reads your words, runs the engine, follows a method
   └─────────────┬──────────────┘
     methods/*.md │ scripts/*.py
   (how to teach) │ (deterministic state: scheduling, files, the board)
                 ▼
            tracks/<id>/   ← your learning, as plain markdown you own
```

Two layers, cleanly split:

- **Portable core** — a deterministic engine (`scripts/`: FSRS scheduling, per-track state files,
  the status board, the daily planner) in Python **standard library only**, plus a **method layer**
  (`methods/*.md`) of pedagogy templates that are just markdown data.
- **Host adapter** — one thin Claude Code skill (`skills/learn/`) that turns your plain-language
  requests into engine calls and teaching loops. **The skill is not the intelligence:** the host
  model does the teaching by following the method layer; the engine only keeps the state honest
  (it never guesses a due date or a card id). An MCP server / other-host adapters are future work —
  the core is designed to slot in without a rewrite.

## The pedagogy toolkit

Teaching method is **data** (`methods/*.md`), chosen automatically by material × learner × goal —
you only ever see the outcome ("I'll walk you through it" / "let me quiz you" / "explain it back").

| Method | For |
|---|---|
| `tutor` | read-along teaching — the default for knowledge/explanatory material |
| `socratic` | lead by questions; let you discover the answer |
| `feynman` | you explain it back; the model probes the gaps |
| `active-recall` | retrieval-practice quizzing — the review default (the FSRS partner) |
| `worked-examples` | procedural / math / coding — study a solved example, then fade the scaffolding |
| `deliberate-practice` | build a performable skill: isolate the edge, drill, immediate feedback |
| `elaboration` | the up-shift for a learner who already has it (transfer, edge cases, compression) |
| `dual-coding` | pair words with a visual; interleave sub-topics |
| `metacognition` | predict-then-compare, plan/monitor/evaluate, catch the illusion of competence |
| `learner-model` | silent per-turn read of grasp/misconception/load that steers every move |
| `learning-science` | the cross-cutting "why": mission, zone of proximal development, storage strength |

## Memory & traceability

learn-everything is built so your learning leaves a durable, inspectable trace — all plain markdown:

- **`CONTEXT.md`** (per track) — the rolling digest read on resume: *Where you are / What you've
  learned / Known sticking points / Open threads.*
- **`learning-records/`** — dated, append-only insights (each corrected misconception, prior
  knowledge, mastery shown).
- **`glossary.md`** — terms you asked about (captured on ask, promoted when you can use them); also
  a map of what was hard.
- **Question heatmap** — every ad-hoc question is logged under a concept; `questions` ranks where
  you asked most (your weak/important spots), which feeds back into what to re-teach and card.
- **`progress`** — three retention numbers per track: total cards / graduated (locked into
  long-term memory) / 7-day accuracy.

Captured misconceptions **feed forward**: the next session re-checks your sticking points first and
corrects the route — skim what you own, dwell on what you missed, re-teach a past slip from a fresh
angle.

## Data model

The **source of truth** is per-track folders under `tracks/`. `registry.json` at the repo root is
only a **rebuildable cache** — it can always be regenerated from the `TRACK.md` files.

```
tracks/<id>/
  TRACK.md            # source of truth: YAML frontmatter (id, title, mode, pedagogy, status,
                      #   created, deadline, last_active, next_action) + "## Goal" + "## Log"
  MISSION.md          # the real-world "why" for this track (grounds every session)
  CONTEXT.md          # rolling memory digest (read first on resume)
  plan.md             # map-of-content: sessions + card wikilinks
  cards/card-0001.md  # frontmatter + "#flashcards/<track>" + question / "?" / answer
                      #   (Obsidian spaced-repetition compatible)
  notes/<date>-*.md   # the source you're reading + the tutor's lesson notes
  learning-records/   # dated decision-grade insights (corrected misconceptions, etc.)
  review-state.json   # FSRS sidecar: per-card stability/difficulty/due/reps/lapses/state
  review-log.jsonl    # append-only grading history
  questions-log.jsonl # append-only ad-hoc questions (the heatmap source)

registry.json         # REBUILDABLE cache of all tracks (never the sole source)
```

If `registry.json` or a `review-state.json` goes missing or corrupt, the engine rebuilds /
degrades gracefully and warns to stderr — it never loses the source of truth and never crashes the
run. Full-file writes are atomic (tmp + rename), safe under Google Drive / Dropbox sync.

<details>
<summary><b>CLI reference (the tutor runs these for you — you rarely need them directly)</b></summary>

The engine is two stdlib scripts. `registry.py` owns all state; `fsrs.py` is the scheduler.

```bash
# orientation & planning
python3 scripts/registry.py status [--today YYYY-MM-DD]        # board, leads with cards due
python3 scripts/registry.py plan-day [--minutes N] [--energy low|normal|high]
python3 scripts/registry.py progress [--track <id|all>]        # total / graduated / 7-day accuracy

# starting & gating a track
python3 scripts/registry.py create-track --id <id> --title <t> --mode domain --pedagogy <p> [--deadline YYYY-MM-DD] [--goal "..."]
python3 scripts/registry.py ingest-check --track <id>          # ready to learn into? (MISSION set?)
python3 scripts/registry.py session-check --track <id>         # did this session leave a card or a reason?

# cards & review
echo '[{"question":"...","answer":"...","tags":["L2"]}]' | python3 scripts/registry.py add-cards --track <id>
python3 scripts/registry.py due [--track <id|all>] [--today YYYY-MM-DD]
python3 scripts/registry.py grade --track <id> --card <card-id> --grade <1-4> [--today YYYY-MM-DD]

# memory & signals
python3 scripts/registry.py log --track <id> --what "..." [--next "..."] [--no-cards-reason "..."]
python3 scripts/registry.py log-question --track <id> --concept "<C>" --question "<Q>" [--term "<T>"]
python3 scripts/registry.py questions [--track <id|all>]       # where you asked most, ranked
python3 scripts/registry.py rebuild                            # rebuild registry.json from TRACK.md

# scheduler (called by registry.py; usable standalone)
python3 scripts/fsrs.py schedule --state '<json|->' --grade <1-4> --now YYYY-MM-DD
```

Grades: `1`=Again `2`=Hard `3`=Good `4`=Easy. When `--today` is omitted it defaults to the system date.
</details>

## Privacy & confidentiality

> **Read this before learning anything sensitive.**

- When you ingest a source, **its text is sent to the host model** (Claude). Don't ingest material
  you aren't authorized to send to a third-party model; confirm first for privileged/client/legal docs.
- Your learning lives under `tracks/`, which is **gitignored** — notes, cards, questions, and memory
  stay local and are never committed by accident. `profile.md`, `registry.json`, `.obsidian/`, and
  `.claudian/` (which can hold your auth token) are gitignored too.
- Ingested source text is treated as **data, not instructions** — imperative phrasing inside a
  document or web page is content to analyze, never a command to obey.

## A note on FSRS

The engine implements **FSRS-6** spaced repetition in pure standard-library Python. It is
**behavior-verified** (tests lock in grade ordering, due-date monotonicity, new-card seeding);
exact numeric parity with the reference implementation is intentionally deferred — the goal is
correct, predictable, well-tested scheduling, not bit-for-bit constant reproduction. Personalized
weights are out of scope until there's real review history.

## Project layout

```
skills/learn/SKILL.md     the single host-adapter skill (+ FEEDBACK.md improvement log)
methods/*.md              the 11-method pedagogy toolkit (data, not code)
scripts/registry.py       all track/card/registry/planner state I/O (stdlib)
scripts/fsrs.py           FSRS-6 scheduler (stdlib)
tests/                    unit tests (44) for the engine
plans/                    design specs, feature designs, architecture/optimization plans
docs/                     audits + the architecture optimization plan
tracks/                   YOUR learning data (gitignored)
```

## Roadmap

The deferred feature backlog (exam & applied track modes, URL / long-document ingestion, an MCP
server, personalized FSRS weights) is **intentionally frozen** until the core loop is demonstrably
sticky for one real learner (≥10 cards on one track, ≥3 review days). Building breadth against an
empty deck is the failure mode this project is deliberately avoiding. Designs for all of it live in
[`plans/specs/2026-06-22-feature-designs.md`](plans/specs/2026-06-22-feature-designs.md).

## Status & honesty

This is **alpha**. What's solid and tested: the deterministic engine, the full state machine, every
CLI, and all file artifacts — end-to-end across every flow (44 unit tests + a from-zero acceptance
run, all green). What only a real session can prove: the **quality of the teaching dialogue itself**
(that depends on the host model). It hasn't yet been battle-tested across months and many subjects —
that's the next milestone, not a build task.

## Contributing

Issues and PRs welcome. Keep the invariants: the core stays pip-free stdlib; markdown files are the
source of truth (`registry.json` is a rebuildable cache); cards stay Obsidian-spaced-repetition
compatible; teaching comes before cards; nothing is persisted without the learner's approval. New
pedagogy is just a new `methods/*.md`. Run `python3 -m unittest tests.test_fsrs tests.test_registry`
before sending a change.

## Credits

- `methods/learning-science.md` adapts pedagogy from the [`teach` skill by Matt Pocock](https://github.com/mattpocock/skills)
  (MIT, © 2026 Matt Pocock) — reframed for learn-everything's track/card/FSRS model.
- FSRS scheduling follows [open-spaced-repetition/py-fsrs](https://github.com/open-spaced-repetition/py-fsrs)
  (FSRS-6); cards are compatible with [obsidian-spaced-repetition](https://github.com/st3v3nmw/obsidian-spaced-repetition);
  the in-Obsidian experience runs on [Claudian](https://github.com/YishenTu/claudian).

## License

MIT — see [LICENSE](LICENSE).
