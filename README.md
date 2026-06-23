# learn-everything

An open-source, AI-collaborative **multi-track learning OS**. It lets one person learn
many different things at once — exam prep, open-ended professional domains, applied
skills — under a single status board, where the host model (Claude today) does the
*teaching* (Socratic questioning, Feynman explain-back, active recall) and a small,
deterministic engine keeps the *state* honest.

## What makes it different

Most learning tools handle one topic at a time: a flashcard app, a single-subject tutor,
a spaced-repetition deck. The thing they all miss is **cross-track orchestration** — the
problem you actually have when you're learning five different things at once, each a
different *kind* of thing, and you lose context every time you switch.

learn-everything is built around two ideas existing tools don't combine:

- **Cross-track orchestration** — every active track lives under one rebuildable status
  board. Ask "what should I do next?" and the system answers across all tracks at once:
  what's due for review, what's stale, what's near a deadline.
- **Per-track pedagogy** — each track picks how it wants to be taught (Socratic / Feynman /
  active recall). The teaching method is *data*, not hard-coded behavior, so a domain track
  and an exam track can be interrogated completely differently.

## Design: core + adapter

The system is split into a **portable core** and a thin **host adapter**. The portable core
is a deterministic engine (FSRS scheduling, per-track state files, the status board) written
in Python standard library only — no `pip`, no Claude-specific code — plus a *method layer*
of pedagogy templates that are just markdown data files; the host adapter today is a single
lightweight Claude Code skill (`skills/learn/`) that orchestrates create / ingest / review by
reading `TRACK.md` files and shelling out to the engine. **The plugin is not the intelligence:**
the host model performs the pedagogy by following the method layer; the engine only supplies
the deterministic scaffolding. An MCP server and other-host adapters are future work — the
core's surface is designed so they slot in without a rewrite.

## Quick start

learn-everything works with **Claude Code** out of the box — point it at the `learn` skill.

```bash
# 1. Clone
git clone <your-fork-url> learn-everything
cd learn-everything

# 2. Use it from Claude Code by invoking the skill at skills/learn/
#    (in a Claude Code session, just ask to "start a learning track" / "review what's due")

# 3. Create a track
python3 scripts/registry.py create-track \
  --id llm-agents --title "LLM & Agents" --mode domain --pedagogy socratic \
  --goal "Understand modern agent architectures"

# 4. Ingest a source (the host model proposes cards; you approve; cards get written)
#    Then add an approved card:
python3 scripts/registry.py add-card --track llm-agents \
  --question "What does FSRS schedule?" --answer "The next review date per card." --tags fsrs

# 5. Review what's due, then grade
python3 scripts/registry.py due --track all
python3 scripts/registry.py grade --track llm-agents --card card-0001 --grade 3
```

Everything is plain files you can read, edit, and version yourself.

## Use it inside Obsidian (one app)

learn-everything's folder is a valid Obsidian vault (markdown + frontmatter + `[[wikilinks]]`
+ a per-track `plan.md` map-of-content), so you can run the whole loop in a single window:

1. **Open the repo as a vault** in Obsidian — source notes, cards, and `plan.md` render on the left.
2. **Add [Claudian](https://github.com/YishenTu/claudian)** (MIT): it embeds Claude Code as a
   sidebar with the vault as its working directory. That sidebar is your tutor — read on the
   left, ask on the right, notes grow live in `tracks/<id>/notes/`.
3. **Add [obsidian-spaced-repetition](https://github.com/st3v3nmw/obsidian-spaced-repetition)**
   (MIT): cards written by `add-card` use its `#flashcards/<track>` + `?`-separator format, so
   they review natively in Obsidian. learn-everything's FSRS engine stays the authoritative
   scheduler (state in `review-state.json`).

> ⚠️ **Verify once on your machine:** the in-Obsidian path needs Claudian's embedded Claude
> Code to run the Python engine via Bash. Expected to work but unverified — test with
> `python3 scripts/fsrs.py schedule --state '-' --grade 3 --now 2026-06-22`. If script
> execution is blocked, run Claude Code in a terminal beside Obsidian (same folder) instead.

## Data model

The **source of truth** is per-track folders under `tracks/`. `registry.json` at the repo
root is only a **rebuildable cache** — it can always be regenerated from the `TRACK.md` files.

```
tracks/<id>/
  TRACK.md            # source of truth: YAML frontmatter (id, title, mode, pedagogy,
                      #   status, created, deadline, last_active, next_action)
                      #   + "## Goal" + "## Log" markdown table
  cards/
    card-0001.md      # frontmatter (id, tags) + "#flashcards/<track>" + question / "?" / answer
                      #   (Obsidian spaced-repetition compatible — reviews natively in Obsidian)
  notes/
    <date>-<slug>.md  # free-form study notes
  plan.md             # map-of-content; wikilinks to cards
  review-state.json   # FSRS sidecar: per-card stability/difficulty/due/reps/lapses/state

registry.json         # REBUILDABLE cache of all tracks (never the sole source)
```

Card ids are zero-padded and sequential per track. New cards seed FSRS `state="new"` with
`due=today`. If `registry.json` or a `review-state.json` is missing or corrupt, the engine
rebuilds / degrades gracefully and warns to stderr — it never loses the source of truth and
never crashes the whole run.

## CLI contract

The engine is two scripts. The skill calls these; you can too.

`scripts/fsrs.py`

| Command | Purpose |
| --- | --- |
| `schedule --state '<json\|->' --grade <1-4> --now YYYY-MM-DD` | Print the new FSRS state for one card. `--state '-'` (or omitted) = brand-new card. Grades: 1=Again, 2=Hard, 3=Good, 4=Easy. |

`scripts/registry.py`

| Command | Purpose |
| --- | --- |
| `create-track --id <id> --title <t> --mode domain --pedagogy <p> [--deadline YYYY-MM-DD] [--goal "..."]` | Scaffold a new track folder and update the registry. |
| `rebuild` | Rescan `tracks/*/TRACK.md` and rewrite/print `registry.json`. |
| `status [--today YYYY-MM-DD]` | Rebuild, then print a board: each track + days to deadline + cards due today + stale flag. |
| `next-card-id --track <id>` | Print the next free card id (e.g. `card-0004`). |
| `add-card --track <id> --question "..." --answer "..." [--tags a,b] [--today YYYY-MM-DD]` | Write a new card and seed its review state. |
| `due [--track <id\|all>] [--today YYYY-MM-DD]` | List due cards (`due <= today`). |
| `grade --track <id> --card <card-id> --grade <1-4> [--today YYYY-MM-DD]` | Grade a card via FSRS, update review state and `last_active`. |
| `log --track <id> --what "..." [--next "..."] [--artifacts "..."]` | Append a `## Log` row and update `last_active` / `next_action`. |

`registry.py` imports `fsrs.py` for grading. When `--today` is omitted it defaults to the
system date.

## Confidentiality & privacy

> **Read this before ingesting anything sensitive.**

- When you ingest a source, **its text is sent to the host model** (Claude) for card
  proposals. Do not ingest material you are not authorized to send to a third-party model.
- The entire `tracks/` directory is **gitignored** — your learning data, notes, and cards
  stay local and are never committed by accident. Only `tracks/.gitkeep` is tracked.
- **Do not commit privileged or client material.** This repo is meant to be published as a
  clean, data-free product; your real tracks live as local, gitignored data.
- For confidential documents (privileged communications, client files, M&A material),
  **confirm authorization before ingesting** — treat the host model as an external service.

Ingested source text is treated as **data, not instructions**: imperative phrasing embedded
in a document or web page is content to analyze, never a command to obey.

## A note on FSRS

The engine implements **FSRS-6** spaced repetition in pure standard-library Python (no
dependencies). It is **behavioral-verified** — covered by tests that lock in scheduling
behavior (grade ordering, due-date monotonicity, new-card seeding). Exact *numeric parity*
with the reference FSRS implementation is intentionally **deferred**: the goal for MVP is
correct, predictable, well-tested behavior, not bit-for-bit reproduction of reference
constants.

## Roadmap

- **`exam` and `applied` modes** — beyond the MVP `domain` mode (the spine is built so they
  slot in without rework).
- **MCP server** — wrap the core's surface as MCP tools / prompts / resources so other hosts
  (and other Claude surfaces) attach without a rewrite.
- **Obsidian companion** — the basic one-app workflow already works today (see *Use it inside
  Obsidian* above); a deeper companion (due-card counts / `next_action` surfaced inside
  Obsidian, two-way FSRS state sync) is the natural next step.

## Credits

- `methods/learning-science.md` adapts pedagogy from the [`teach` skill by Matt Pocock](https://github.com/mattpocock/skills)
  (MIT, © 2026 Matt Pocock) — reframed for learn-everything's track/card/FSRS model.
- FSRS scheduling follows [open-spaced-repetition/py-fsrs](https://github.com/open-spaced-repetition/py-fsrs)
  (FSRS-6); cards are compatible with [obsidian-spaced-repetition](https://github.com/st3v3nmw/obsidian-spaced-repetition).

## License

MIT — see [LICENSE](LICENSE).
