# Learning OS Design Spec

> Product name: **learn-everything** (decided 2026-06-22). The working directory IS the repo
> root — files live at the repo root, not under a subfolder. An AI-collaborative
> learning system that orchestrates *multiple parallel learning tracks of different types*
> under one status board, where the host LLM does the teaching (Socratic questioning, Feynman
> explain-back, active recall) and a deterministic engine keeps state honest.
> Bilingual (English-first code/docs, Chinese-capable at runtime), open-source product.
>
> **Three orthogonal axes** (the design skeleton):
> - **Mode** — what kind of track: `domain` / `exam` / `applied`. Picks the workflow.
> - **Pedagogy** — how the AI teaches/interrogates: `socratic` / `feynman` / `active-recall` /
>   `worked-example`. Executed by the host model from method prompts.
> - **Engine** — the deterministic part: FSRS scheduling, state files, status board. Pure scripts,
>   model-independent — never improvised by the LLM.
>
> **The plugin is not the intelligence.** The host model (Claude today) performs the pedagogy by
> following the method layer; the plugin supplies (a) that method layer and (b) the deterministic
> scaffolding. Claude Code skills are merely *one packaging* of the method layer.

## Goal

Give one person learning many different things at once (exam prep, open-ended
professional domains, applied tech skills) a single Claude Code system that (a) knows
every active track and what to do next on each, (b) makes knowledge stick via spaced
repetition, and (c) keeps each track's materials/notes/state in one predictable place
so switching tracks never loses context. The same codebase ships as a clean open-source
plugin (no private data baked in) and serves the author's real tracks as gitignored data.

## Non-Goals

- **MVP excludes `exam` and `applied` modes.** Only the orchestration spine + `domain`
  mode + shared review engine ship first. (IELTS already covers `exam` via the author's
  existing private `ielts-*` skills; that suite is NOT migrated or wrapped in MVP.)
- **No web dashboard / server** in MVP. CLI/skill interaction only. (claude-tutor's
  localhost dashboard is explicitly out — adds a server + security surface for no MVP value.)
- **No full plugin scaffolding in MVP — skill-first.** No `.claude-plugin/` manifest, marketplace
  entry, `commands/`, or `hooks/`. MVP is one `learn` skill + `scripts/` + `methods/`. Per user
  priority: lightweight, effect-first; add scaffolding only when it earns its keep (e.g. at publish).
- **MVP ships only the Claude Code adapter.** The MCP server and other-host adapters
  (ima / Kimi / WorkBuddy) are phase 2+. MVP only *designs the seam* (core/adapter split) so they
  cost little later — it does not implement them. Per-host MCP-support feasibility is unverified
  and must be checked before committing to any specific host adapter.
- **Not integrated into the author's private legal repo routing.** This is a standalone
  product repo; it does NOT touch `trigger-registry.json`, `auto-trigger.md`, or any
  arbitration/legal control plane. Installing it for personal use is a separate plugin-install step.
- No automatic ingestion of sources. Human approves what becomes a card (carried over
  from knowledge-mgmt's human-in-the-loop principle).
- No multi-user / cloud sync / accounts. Local files only.

## Context Checked

- **Working directory** `…/我的云端硬盘/learn everything/` — empty, fresh, not a git repo.
  Confirmed the right place to build a new product from scratch.
- **Existing GitHub solutions surveyed** (none is a drop-in for the mixed need):
  - [kirilxd/claude-tutor](https://github.com/kirilxd/claude-tutor) — `/learn`→`/quiz`→
    SM-2→`/dashboard`; JSON data model under `~/.claude/learning/`. Best for single-topic
    exam-style learning. Borrowed: plan→study→quiz→review cycle, profile.json idea.
  - [owenliang60-ship-it/knowledge-mgmt](https://github.com/owenliang60-ship-it/knowledge-mgmt)
    — `/read /insights /note /review /query /lint`; Obsidian markdown vault, atomic cards,
    domain MOCs, FSRS-6 (stdlib python, no deps), human-approved card writes. Best for
    open-ended domain accumulation. Borrowed: atomic card + MOC structure, FSRS engine,
    dual-proposal human-in-the-loop, markdown-first portability.
  - learn-faster-kit, m98/fluent (language-specific) — confirm the space but add nothing new.
  - **Gap none fills:** cross-track orchestration ("I'm learning 5 things, each a different
    type, and lose context switching"). This is Polylearn's differentiator.
- **Author's repo patterns reused conceptually (not as code deps):** `STATE.md` state-file
  convention (from arbitration) → `TRACK.md`; memory/instinct directories show comfort with
  file-based state.
- **Author's real tracks driving the design:** 换股重组 (share-swap restructuring),
  制造业常年法律顾问 (manufacturing general counsel), LLM/Agent knowledge, IELTS.
- **Security rule** `rules/common/security.md` DATA_BOUNDARY: domain mode ingests external
  content (pasted articles, PDFs, legal docs) → must treat as DATA, not instructions.

## Recommended Approach

**Hybrid (decoupled core + Claude Code adapter now + MCP seam for later).** Not Claude-only
(would hard-bind delivery and kill extensibility) and not MCP-first (premature, worse
dogfooding before the design is proven). Concretely:

- **Portable core (platform-independent):** the Engine (FSRS + state + status helpers, stdlib
  Python, no pip deps), the Method layer (Socratic/Feynman/active-recall prompt templates as
  data files), and the Data model (markdown cards + JSON state). Zero Claude-specific code.
- **Host adapter #1 = ONE lightweight Claude Code skill (MVP) — keep it small.** Per user
  priority: ship a single `learn` skill (one SKILL.md) that orchestrates create/resume/status/
  ingest/review by reading `TRACK.md` and shelling out to `scripts/` + loading `methods/`. The
  heavy logic lives in scripts (SKILL.md stays thin and maintainable). **No** `.claude-plugin/`
  manifest, marketplace entry, `commands/`, `hooks/`, or dashboard in MVP — those are added only
  when they earn their keep. Effect-first, not scaffolding-first.
- **Publish-time wrapper (deferred, cheap):** turning the skill into a distributable open-source
  plugin = adding a thin `.claude-plugin/` manifest around the same files at publish time. It does
  not change the core, so deferring it costs nothing now.
- **MCP seam (designed in MVP, implemented phase 2):** the core's public surface (the functions
  in §Interfaces) is defined so it can be wrapped as an MCP server — exposing Engine ops as MCP
  *tools*, pedagogy templates as MCP *prompts*, tracks as MCP *resources* — with no rewrite. Other
  hosts (ima / Kimi / WorkBuddy) attach via MCP if they support it, or re-express the method layer
  in their native extension model (custom assistant / knowledge base / system-prompt injection).

MVP ships the spine + one mode + pedagogy + the shared engine:
- **Spine** = `registry.json` (rebuildable cache) + per-track `TRACK.md` (source of truth)
  + `/learn` router + `/learn-status` board.
- **One mode** = `domain` (read → propose atomic cards → human approves → write cards/notes,
  update MOC + TRACK, seed review state).
- **Pedagogy (first-class, not deferred)** = the `domain` track and review support
  `feynman` (user explains back, host model judges + probes gaps), `socratic` (host model leads
  with questions instead of exposition), and `active-recall` (plain recall quiz — the natural
  partner of FSRS). Selectable per track (`pedagogy:` in TRACK.md); default `socratic` for ingest,
  `active-recall` for review. Other mainstream techniques (elaboration, worked-example, interleaving)
  are just additional `methods/*.md` files — addable anytime with zero engine change, so they stay
  out of MVP scope without closing the door.
- **Shared engine** = FSRS-6 spaced repetition in stdlib Python (no pip deps), used by
  `/review` across all tracks.

Mechanics are borrowed from the two mature projects (proven); the new design work is (1) the
spine + mode-polymorphism contract so `exam`/`applied` slot in later, and (2) the core/adapter
split + MCP seam so other hosts slot in later — both without rework.

## Alternatives Considered

| Option | Tradeoff | Decision |
|---|---|---|
| Adopt knowledge-mgmt wholesale | Fastest; but single-vault, no cross-track board, no mode concept, English-only, not the author's product | Rejected — borrow mechanics, not the package |
| Adopt claude-tutor wholesale | Good exam loop + dashboard; but single-topic, JSON-not-markdown (less portable), server surface | Rejected — borrow the cycle only |
| Spine-only (no mode) MVP | Smallest; solves "where am I" only | Rejected by user — wants knowledge to stick too |
| All 3 modes at once | Complete; long, risky, hard to validate the spine contract early | Deferred — `domain` first proves the contract |
| Markdown cards + sidecar FSRS state | Slightly more files | **Chosen** — keeps cards Obsidian-portable, engine state isolated |

## Design

### Components

1. **`learn` (the single MVP skill / host adapter)** — one thin SKILL.md that orchestrates all
   user-facing actions by reading `TRACK.md`, shelling to `scripts/`, and loading `methods/`.
   Deterministic work is delegated to scripts so the SKILL.md stays small. It performs four actions
   (triggered by natural language, or an optional single `/learn` command):
   - **status** — cross-track overview (default when invoked with no specific intent). For each
     non-archived track: title, mode, pedagogy, status, days-to-deadline, # cards due today,
     last-active, next action. Rebuilds from `TRACK.md` files if `registry.json` is missing/stale;
     flags overdue deadlines and stale tracks (no activity > N days). Backed by `scripts/registry.py`.
   - **create** — new track: ask `mode` (default `domain`), `pedagogy` (default `socratic`), title,
     optional deadline; scaffold the track folder + `TRACK.md`; register.
   - **resume** — existing track: read `TRACK.md`, show `next_action`, continue in its mode/pedagogy.
   - **ingest (domain loop)** — take one source (pasted text / file path / URL via the web-access
     boundary). Following the track's `methods/<pedagogy>.md` template, produce a **Map** (narrative
     summary) + propose **atomic cards** (Q/A, one idea each). **Human approves which cards** before
     any write. On approval, write cards to `cards/`, append source + Map to `notes/`, update
     `plan.md` (domain MOC) with wikilinks, update `TRACK.md` (log + new `next_action` + `last_active`),
     seed FSRS state in `review-state.json`.
   - **review** — collect cards with `due <= today` across all tracks (or one if named). For each,
     run the track's pedagogy (e.g. `feynman`: explain-back + gap-probe; `active-recall`: show Q,
     take recall), grade 1–4 (again/hard/good/easy), call `scripts/fsrs.py`, write back state,
     update `last_active`.
5. **`scripts/fsrs.py` (review engine)** — FSRS-6 scheduler, Python stdlib only. Pure functions:
   `schedule(card_state, grade, now) -> new_card_state`. No I/O; skills handle file reads/writes.
6. **`scripts/registry.py` (status helpers)** — rebuild `registry.json` from `TRACK.md` files;
   allocate next card id; collect due cards. Stdlib only.
7. **`methods/` (pedagogy layer — data, not code)** — one file per pedagogy
   (`socratic.md`, `feynman.md`, `active-recall.md`, …) holding the instruction template the
   host model follows for that teaching style. Mode skills load the track's chosen method file.
   Platform-independent (becomes MCP *prompts* in phase 2). This is the "AI collaboration" content;
   the host model is what executes it.

### Architecture: core vs host adapters

- **Portable core** (`scripts/` engine + `methods/` pedagogy + data formats) contains zero
  host-specific code. Its public surface = the function signatures in §Interfaces.
- **Host adapter** wires a specific host's UI/agent to that surface. MVP adapter = a single
  Claude Code skill (`skills/learn/SKILL.md`, no commands/manifest): the skill markdown tells
  Claude when to call `scripts/`, when to load a `methods/` template, and how to run the multi-turn
  Socratic/Feynman loop.
- **MCP seam (phase 2):** wrap the core as an MCP server — Engine ops → MCP *tools*
  (`fsrs_schedule`, `due_cards`, `rebuild_registry`, `alloc_card_id`), pedagogy → MCP *prompts*,
  tracks/cards → MCP *resources*. Any MCP-capable host then drives Polylearn with no core rewrite.
- **Non-MCP hosts** (if a target lacks MCP) re-express only the adapter: port the method templates
  into that host's custom-assistant / knowledge-base / system-prompt mechanism; the engine still
  runs as standalone scripts the host shells out to (or as a tiny local service).
- **Honest limit:** the engine and state port everywhere, but *Socratic/Feynman dialogue quality
  scales with the host model's capability* — weaker hosts give degraded pedagogy, same data.

### Interfaces

**Command surface (MVP):** one skill `learn`, invoked by natural language (status / create /
resume / ingest / review are intents the skill disambiguates). An optional single `/learn`
command may alias it. No per-action commands — keeps the surface minimal.

**Repo / data layout (lightweight, skill-first):**
```
polylearn/                      # open-source repo (this product)
  skills/learn/SKILL.md         # the single MVP skill (thin orchestrator)
  scripts/                      # fsrs.py, registry.py (stdlib only) — the portable engine
  methods/                      # socratic.md, feynman.md, active-recall.md — pedagogy templates
  tests/                        # unit + integration
  README.md  README.zh.md  LICENSE(MIT)  .gitignore
  profile.example.md
  tracks/.gitkeep               # author's real tracks live here, GITIGNORED
  # .claude-plugin/ (manifest+marketplace) and any MCP wrapper are ADDED LATER at publish time
```

**`TRACK.md` (per track, source of truth):**
```markdown
---
id: share-swap-restructuring
title: 换股重组
mode: domain            # domain | exam | applied (only domain in MVP)
pedagogy: socratic      # socratic | feynman | active-recall (host model executes this)
status: active          # active | paused | done | archived
created: 2026-06-22
deadline: null          # ISO date or null
last_active: 2026-06-22
next_action: 读《XX指引》第2章，产出3张卡
---
## Goal
<one paragraph>
## Log
| date | what happened | artifacts |
|------|---------------|-----------|
| 2026-06-22 | 建轨；读完导论 | notes/2026-06-22-intro.md, cards 0001-0003 |
```

**`registry.json` (rebuildable cache; never the sole source):**
```json
{ "tracks": [ { "id": "share-swap-restructuring", "title": "换股重组",
  "mode": "domain", "status": "active", "deadline": null,
  "last_active": "2026-06-22", "next_action": "...", "cards_total": 3 } ] }
```

**Card file `cards/card-0001.md`:**
```markdown
---
id: card-0001
tags: [换股重组, 对价]
---
**Q:** 换股重组中"换股比例"如何确定？
**A:** <answer>
```

**`review-state.json` (per track, FSRS state keyed by card id):**
```json
{ "card-0001": { "stability": 3.2, "difficulty": 5.1, "due": "2026-06-23",
  "reps": 1, "lapses": 0, "last_review": "2026-06-22", "state": "review" } }
```

### Data / State

- **Source of truth = the `TRACK.md` files.** `registry.json` is a derived cache and must be
  rebuildable by scanning `tracks/*/TRACK.md`.
- **Cards stay clean and portable** (Obsidian-compatible markdown); all scheduling state lives in
  the sidecar `review-state.json`, so cards can be edited/exported without touching the engine.
- **Card ids** are zero-padded sequential per track (`card-0001`); allocator reads the max
  existing id to avoid collisions.
- **Open-source vs personal split:** code carries zero personal content; `tracks/` is gitignored;
  `profile.example.md` shipped, real `profile.md` gitignored.

### Failure Modes

- **`registry.json` missing/stale/corrupt** → `/learn-status` rebuilds from `TRACK.md` files; warn.
- **`review-state.json` missing/corrupt for a track** → treat its cards as new (re-seed), warn the
  user that scheduling history for that track was lost; never crash the whole `/review`.
- **Card id collision** → allocator enforces max-existing+1; on detected duplicate, abort the write
  and report.
- **User abandons a domain ingest before approval** → nothing is written (cards/notes/MOC/state are
  written only on approval, as one batch); a partial run leaves the track unchanged.
- **Deadline passed / track stale** → status board flags, does not auto-archive.
- **Untrusted ingested content (DATA_BOUNDARY)** → domain mode wraps fetched/pasted source text as
  DATA, never instructions; scans for injection patterns (e.g. "ignore previous instructions",
  hidden/zero-width chars, "忽略前面") and flags `[PROMPT_INJECTION_DETECTED]` rather than obeying.
- **Confidential material (legal tracks)** → README warns that source text is sent to the model;
  `tracks/` gitignored so privileged content never enters the public repo. Author confirms before
  ingesting sensitive case material.
- **FSRS bad input (unknown grade, null state)** → engine validates grade ∈ {1,2,3,4}; new card
  with no prior state uses defined initial values; raises a clear error rather than silent default.

### Verification

- **Unit (`scripts/`):**
  - `fsrs.py`: known `(state, grade, now)` inputs produce expected next-due/stability (test against
    a small reference vector set); grade validation rejects out-of-range.
  - `registry.py`: rebuild from a fixture of `TRACK.md` files yields the expected `registry.json`;
    card-id allocator returns max+1; due-card collector filters by `due <= today`.
- **Integration (end-to-end, the MVP acceptance test):**
  1. `/learn "换股重组"` → creates `tracks/share-swap-restructuring/` with a valid `TRACK.md`,
     registers it.
  2. In the track, ingest a sample source → approve 3 proposed cards → assert 3 `cards/*.md`,
     `notes/` entry, `plan.md` MOC links, 3 entries in `review-state.json`, `TRACK.md` log + new
     `next_action`.
  3. `/learn-status` lists the track with `cards_total: 3` and the next action.
  4. Simulate `now = created + 1 day`; `/review` surfaces the 3 due cards; grade them; assert their
     `due` dates advance per FSRS.
- **Pedagogy (method layer):** with `pedagogy: feynman`, the ingest/review loop asks the user to
  explain a concept back and the host model probes a gap rather than just revealing the answer;
  switching the track to `socratic` changes the interaction to question-led. Verifies the method
  files actually drive host behavior (manual/eval check, since it's model-behavioral).
- **Core portability:** the Engine runs standalone — `python scripts/fsrs.py` and
  `python scripts/registry.py` (or their test harness) execute with no Claude/host present and no
  pip installs, proving the core has zero host coupling (the precondition for the MCP seam).
- **Product (clean-clone):** fresh clone with empty `tracks/`, no private data; `/learn "Test"`
  creates a track end-to-end; README install steps reproduce it; `.gitignore` confirmed to exclude
  `tracks/` and `profile.md`.

### Documentation / Routing Impact

- New standalone repo. Ships `README.md` (English) + `README.zh.md` (Chinese), `LICENSE` (MIT),
  `.claude-plugin/` manifest + marketplace entry, `profile.example.md`.
- **No change to the author's private legal control plane** (no `trigger-registry.json` /
  `auto-trigger.md` edits). Personal use = install Polylearn as a plugin separately.
- Future (post-MVP) docs note: `exam`/`applied` modes and an optional IELTS example track.

## Open Items

- ~~**Final product name.**~~ RESOLVED 2026-06-22: **learn-everything**.
- **`/review` default scope** — all tracks vs. ask which track each session. Lean: all due cards by
  default, `--track` to narrow. Confirmable during `/plan`.
- **Stale-track threshold N days** for the status-board flag (default proposal: 7). Tunable.
- **Whether to publish to a Claude plugin marketplace now or after dogfooding** — product decision,
  not a design blocker.
- **Multi-host adapters (ima / Kimi / WorkBuddy) — phase 2+, needs verification.** Each host's
  feasibility depends on whether it supports MCP or otherwise allows method-layer injection (custom
  assistant / knowledge base / system prompt). Current per-host MCP support is *unverified* in this
  spec; do a quick capability check before building any specific adapter. The MVP seam (core/adapter
  split) is what keeps this cheap regardless of which host wins.
- **Obsidian integration (future direction, NOT in MVP — user suggestion, not a decision).** The
  data model is already chosen to be Obsidian-friendly: cards are markdown with frontmatter +
  `[[wikilinks]]`, `plan.md` is a MOC, and a `tracks/<id>/` folder opens directly as an Obsidian
  vault — so no rework is needed to support this later. Possible later layers: (a) document
  "open `tracks/` as a vault" in the README (near-zero cost); (b) a companion Obsidian plugin
  surfacing due-card counts / `next_action` from `registry.json` inside Obsidian; (c) two-way sync
  of FSRS state with an Obsidian SR plugin. Revisit after MVP dogfooding; keep markdown/wikilink
  formats stable so any of these stays cheap.
