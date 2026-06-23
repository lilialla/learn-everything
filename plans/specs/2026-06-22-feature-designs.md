# learn-everything — Feature Designs

> These are the **detailed feature designs** for the roadmap items and Open Items of the main
> spec, [`2026-06-22-learning-os-spec.md`](./2026-06-22-learning-os-spec.md). The MVP (spine +
> `domain` mode + shared FSRS engine, the single `learn` skill, `methods/*.md`) has shipped; this
> document specifies the **deferred/post-MVP** features it leaves as roadmap. Every design below
> honors the project's non-negotiable invariants:
>
> - **Portable CORE stays pip-free** (stdlib Python: `scripts/fsrs.py`, `scripts/registry.py`).
>   Anything needing pip / network / browser / OCR is an **optional out-of-core adapter**
>   (under a new top-level `adapters/`), never imported by CORE or the `learn` skill's core path.
> - **Markdown is the source of truth**; `registry.json` is a rebuildable cache. Cards stay
>   Obsidian-spaced-repetition compatible (`#flashcards/<track>` + `?`). State lives in `TRACK.md`
>   + `review-state.json`.
> - **Skill-first host adapter** (one thin `skills/learn/SKILL.md`). No `.claude-plugin/` manifest,
>   `commands/`, `hooks/`, or dashboard until publish. MCP server stays a designed seam (phase 2).
> - **REUSE, don't rebuild** — wrap the author's existing skills (`mineru-ocr`,
>   `case-files-to-md(-fast)`, `video-notes`, `funasr-transcribe`, `wechat-article-fetch`,
>   `web-crawl-workflow`, `md2word`) and proven libs (`py-fsrs`, `genanki`, `fsrs-optimizer`,
>   `obsidian-spaced-repetition`) rather than reimplement.
> - **Human-in-the-loop** approval for everything that enters the knowledge base; teaching-first,
>   cards are the safety net.
> - **DATA_BOUNDARY** — ingested/scraped/OCR'd content is UNTRUSTED data, never instructions.
> - **Confidentiality** — `tracks/`, `registry.json`, `profile.md` gitignored; confirm before
>   sending confidential material to the host model.

---

## Completeness Matrix

Every roadmap item + Open Item from the main spec, mapped to its design here.

| Roadmap / Open Item (main spec) | Status | Section |
|---|---|---|
| **URL → md ingestion** ("send a link, learn it") — Open Items §"URL → md ingestion" | Specified here ✓ | [URL → md Ingestion Adapter](#url--md-ingestion-adapter-send-a-link-learn-it) |
| **Long-document / book / large-PDF ingestion** — referenced by the URL roadmap ("if large → hand to long-document-ingestion") but not separately specced in the spec | Specified here ✓ (new, fills the referenced-but-unspecced gap) | [Long-Document Ingestion](#long-document-ingestion-books--large-pdfs) |
| **`exam` mode** — Non-Goals §"MVP excludes exam" (deferred, not designed) | Specified here ✓ | [Exam Mode](#exam-mode) |
| **`applied` mode** — Non-Goals §"MVP excludes applied" (deferred, not designed) | Specified here ✓ | [Applied Mode](#applied-mode-learn-by-building) |
| **Cross-track orchestration** ("the differentiator") — Recommended Approach; status board is MVP, daily planning is the deepening | Specified here ✓ | [Daily Plan Generator](#daily-plan-generator-plan-day) |
| **FSRS numeric parity with py-fsrs** — caveat in shipped `scripts/fsrs.py` header ("PARITY DEFERRED") | Specified here ✓ | [Engine Hardening](#engine-hardening-fsrs-parity--personalized-weights--configurable-retention) |
| **Personalized FSRS weights** (`fsrs-optimizer`) — implied by FSRS engine choice | Specified here ✓ | [Engine Hardening](#engine-hardening-fsrs-parity--personalized-weights--configurable-retention) |
| **Configurable requested-retention** — hardcoded `0.9` in shipped `fsrs.py` | Specified here ✓ | [Engine Hardening](#engine-hardening-fsrs-parity--personalized-weights--configurable-retention) |
| **Anki export adapter** — referenced as the canonical out-of-core adapter pattern (Open Items, repeatedly) | Specified here ✓ | [Interop & Export Adapters](#interop--export-adapters-anki--obsidian-companion) |
| **Obsidian integration** — Open Items §"Obsidian integration": (a) README vault note, (b) companion plugin surfacing due counts, (c) two-way FSRS sync | **Partial** — (a) done in MVP; (b) Tier-1 dashboard-note specified ✓ + Tier-2 plugin = documented seam; (c) explicitly resolved as **render-only, single FSRS writer** (no two-way sync) | [Interop & Export Adapters](#interop--export-adapters-anki--obsidian-companion) |
| **Publish-time plugin wrapper** (`.claude-plugin/` manifest + marketplace) — Recommended Approach §"Publish-time wrapper" / Non-Goals §"skill-first" | Specified here ✓ | [Publish & Packaging](#publish--packaging) |
| **CI + example track + CHANGELOG / SemVer** — implied by "distributable open-source product" | Specified here ✓ | [Publish & Packaging](#publish--packaging) |
| **`/review` default scope** (all tracks vs. ask) — Open Items | **Partial** — leaning "all due by default, `--track` to narrow" is consumed by the [Daily Plan Generator](#daily-plan-generator-plan-day) (`--track` filter); not a standalone section | [Daily Plan Generator](#daily-plan-generator-plan-day) |
| **Stale-track threshold N=7 days** — Open Items | **Partial** — reused as a constant by the daily planner's `stale_pressure`; surfaced, tunable, not independently re-litigated | [Daily Plan Generator](#daily-plan-generator-plan-day) |
| **MCP server / seam (phase 2)** — Recommended Approach §"MCP seam", Non-Goals | **Gap (intentional)** — not designed in detail here; every new CORE function added below (`structure.py`, `exam.py`, `plan_day`, `load_weights`) is kept stdlib + side-effect-explicit specifically to remain MCP-wrappable later. Designed-for, not implemented. |
| **Multi-host adapters** (ima / Kimi / WorkBuddy) — Open Items, "needs verification" | **Gap (intentional)** — out of scope for these designs; unblocked by the same core/adapter split. Capability check still required before building any specific host adapter. |
| **Publish to marketplace now vs. after dogfooding** — Open Items | **Gap (product decision)** — mechanics specified in [Publish & Packaging](#publish--packaging); the *timing* is left to the author, not resolved here. |

---

## Build Order (prioritized, for the deferred features)

The features split into **"do now / MVP-adjacent"** (cheap, additive, no new deps) and
**"phase 2"** (modes + dep-bearing adapters). Recommended sequence:

**Tier 0 — ship now, alongside the MVP (no new runtime deps, additive):**
1. **Engine Hardening (1): FSRS parity oracle** — dev/CI only, closes a caveat already written
   into shipped `fsrs.py`. Zero runtime risk.
2. **Engine Hardening (3): configurable retention + (writer only) review-log** — the
   `schedule()`/`next_interval()` seams already accept the args; this is CLI/frontmatter plumbing.
   Ship the `review-log.jsonl` *writer* now so optimizer data accrues from day one.
3. **Daily Plan Generator (`plan-day`)** — the deepening of the MVP status board, the project's
   single genuine differentiator. Pure additive change to `registry.py` + one `methods/` file.
4. **Interop (1): Obsidian dashboard-note + `due_today` registry field + single-FSRS-writer
   decision** — stdlib-only, immediate dogfood value inside Claudian.

**Tier 1 — at publish time:**
5. **Publish & Packaging** — `.claude-plugin/` manifest + marketplace, CHANGELOG/SemVer,
   `examples/demo-track/`, CI (unittest matrix + the parity job from #1). Additive, no core change.

**Tier 2 — phase 2 (after dogfooding produces real data, dep-bearing):**
6. **URL → md ingestion adapter** — isolated, touches no engine code. Spike yt-dlp + a scraper
   on 1 real article + 1 real video first.
7. **Long-Document Ingestion** — builds *on* the URL adapter (it hands large PDFs/transcripts
   here). Prove `structure.py` + `methods/reading-guide.md` on already-extracted md before wiring OCR.
8. **Exam mode** and **Applied mode** — validations of the spine's mode-polymorphism contract that
   `domain` proves first. Each adds only a method file + a SKILL.md branch + additive `TRACK.md`
   fields (+ `scripts/exam.py` for exam). Sequence either order; both unblock the `mastery_gate`
   hook designed into the daily planner.
9. **Engine Hardening (2): personalized weights** (`fsrs-optimizer`, pulls torch) — out-of-core
   adapter, meaningful only once review history exists (the writer from #2 feeds it).
10. **Interop (2–4): Anki `.apkg` export → AnkiConnect push → optional Tier-2 Obsidian plugin** —
    each self-contained, gated on `genanki` / a connected AnkiConnect MCP / dogfeeding results.

> **Invariant flags:** No design below violates the invariants. The two places that come closest
> and how they are kept honest: (a) **personalized weights / optimizer** pull `torch` — quarantined
> in `adapters/fsrs_optimize/` and *never* imported by CORE, with a CI grep gate asserting
> `scripts/fsrs.py` imports nothing outside stdlib; (b) **Obsidian/Anki two-way FSRS sync** would
> create a second scheduler — explicitly **rejected**; adapters are strictly read-only on
> `review-state.json`, leaving `scripts/fsrs.py` the one authoritative writer.

---

## Daily Plan Generator (`plan-day`)

### Goal
Turn the existing read-only status board (per-track due counts / stale / deadline) into a
**concrete, prioritized, time-boxed session list for today**, across every active track at once.
The output is the thing no surveyed competitor produces (the cross-track learning-OS differentiator
the spec singles out): *"20 min — review 换股重组's 12 due cards; 30 min — new chapter on LLM/Agent
track; 5 min — re-anchor IELTS (stale 9 days)."* The **engine ranks and time-boxes deterministically**;
the **host model only narrates** the ranked plan into tutor-voice prose and then executes each block
via the existing `resume`/`ingest`/`review` actions. This keeps the differentiator honest
(reproducible, testable) rather than an LLM vibe-guess.

### Logic flow (numbered, end-to-end)
1. **Inputs gathered (engine, no model):** `plan-day` calls the existing `rebuild_registry()` →
   `status_board()` path to get, per non-archived/active track: `mode`, `pedagogy`, `status`,
   `days_to_deadline`, `cards_due_today`, `last_active`, `stale`, plus `next_action` from
   `read_track()`. It additionally reads two new optional `TRACK.md` frontmatter fields
   (`goal_weight`, `minutes_per_new_block`) and a new optional `profile.md` block (time budget +
   energy). All have defaults so old tracks/profiles keep working.
2. **Candidate generation:** each track contributes up to three *candidate blocks*:
   - `review` block — emitted iff `cards_due_today > 0`. Estimated minutes =
     `ceil(cards_due_today × sec_per_card / 60)` (default `sec_per_card = 40`, profile-overridable).
     Capped at `max_review_block_min` (default 25) so one giant backlog can't eat the whole day;
     overflow cards stay due tomorrow (FSRS already tolerates this).
   - `new` block — emitted iff track `status == active` and it has a `next_action`. Estimated
     minutes = `minutes_per_new_block` (default 30).
   - `re-anchor` block — emitted iff `stale` is true AND no `review`/`new` block already chosen for
     that track. Fixed small estimate `reanchor_min` (default 5): a quick "what was this track
     about / skim last note" touch to stop decay.
3. **Scoring (deterministic, pure `score_block`):** each candidate gets a numeric priority (see
   §Prioritization logic). No randomness; ties broken by a fixed key (deadline asc, then track id
   asc) so output is byte-stable for a fixed input + `--today`.
4. **Interleaving pass:** sort blocks by score desc, then a round-robin de-clustering so the final
   list doesn't stack three blocks of the same track back-to-back when other tracks wait
   (interleaving as a first-class orchestration signal). Interleaving only reorders *within* score
   bands, never promotes a low-priority block above a high one.
5. **Time-budget fitting (greedy by score):** walk the scored+interleaved list, accumulating
   estimated minutes until `time_budget_min` (from profile / `--minutes`, default 60). Blocks that
   fit are `scheduled`; the rest are `deferred` (reason `over_budget`) so the user sees what was
   dropped. A hard-deadline block (within `urgent_days`, default 3) is force-included even if it
   overflows and is flagged `budget_exceeded_for_deadline`.
6. **Energy adaptation (deterministic mapping):** profile `energy: low|normal|high` (or `--energy`)
   shifts ordering and budget: `low` → demote `new` blocks below `review`/`re-anchor` and shrink
   `minutes_per_new_block` by a fixed factor; `high` → allow one extra `new` block over budget. A
   lookup table in the engine, so it's reproducible.
7. **Engine emits structured plan (JSON):** ordered `scheduled[]` blocks each with
   `{track, title, action, kind, est_min, due_count, reason_codes[], score}`, a `deferred[]` list,
   and a `summary` (`total_min`, `budget_min`, `tracks_touched`). **Engine writes nothing** —
   `plan-day` is read-only (like `status`/`due`).
8. **Model narrates (host adapter, `methods/daily-plan.md`):** `skills/learn/SKILL.md` shells
   `python scripts/registry.py plan-day --today … --json`, then renders the *given order and
   time-boxes verbatim* into tutor prose, reading `profile.md` only for tone/language. The SKILL
   prompt forbids re-ranking ("the engine has already prioritized; present blocks in the given
   order, do not reorder or invent blocks"). A `[PLAN]` header lists the blocks; the model then
   offers to start block 1 by invoking the matching existing action (`review --track X`, or
   `resume`/`ingest` for `new`).
9. **Execution loop:** when the user finishes a block, the existing action already calls
   `grade_card`/`log_entry`, which bump `last_active` and rebuild the registry — so re-running
   `plan-day` later the same day reflects completed work (finished review blocks drop out; touched
   tracks lose `stale`). No new "what's done today" state needed — it falls out of the source of truth.

### Components
1. **`scripts/registry.py` additions (the engine):** pure functions `candidate_blocks(today, root)`,
   `score_block(block, today, weights)`, `plan_day(today, budget_min, energy, root) -> dict`, plus a
   `plan-day` CLI subcommand. Stdlib-only, reusing `status_board`, `read_track`, `due_cards`,
   `_days_between`, `_today_str` already present — honors the pip-free CORE invariant.
2. **`methods/daily-plan.md` (NEW narration template — data, not code):** instructs the host model
   how to read the engine's JSON and speak it as a coach, with the explicit *do-not-reorder /
   do-not-invent* guardrail. The orchestration counterpart to `methods/tutor.md`.
3. **`profile.md` additions (optional):** a `## Time & energy` block the engine parses for defaults
   (budget, sec/card, energy). Shipped in `profile.example.md`.

### Interfaces (CLI subcommands / file formats / method files)
```
python scripts/registry.py plan-day [--today YYYY-MM-DD] [--minutes N]
                                     [--energy low|normal|high]
                                     [--track ID]        # plan just one track  (= the spec's `/review --track` narrowing)
                                     [--json]            # default human table otherwise
```
Returns (JSON):
```json
{ "today": "2026-06-23", "budget_min": 60, "energy": "normal",
  "scheduled": [
    {"track":"share-swap-restructuring","title":"换股重组","kind":"review",
     "action":"review --track share-swap-restructuring","est_min":8,"due_count":12,
     "score":91.0,"reason_codes":["deadline_soon","high_goal_weight"]},
    {"track":"llm-agents","title":"LLM/Agent","kind":"new",
     "action":"resume --track llm-agents","est_min":30,"due_count":0,
     "score":52.0,"reason_codes":["active_next_action"]},
    {"track":"ielts","title":"IELTS","kind":"re-anchor",
     "action":"resume --track ielts","est_min":5,"due_count":0,
     "score":40.0,"reason_codes":["stale_9d"]}
  ],
  "deferred":[{"track":"manufacturing-gc","kind":"new","est_min":30,"reason":"over_budget"}],
  "summary":{"total_min":43,"budget_min":60,"tracks_touched":3} }
```
**New `TRACK.md` frontmatter (both optional, defaulted):**
```yaml
goal_weight: 1.0          # 0.5–2.0 multiplier on this track's priority; default 1.0
minutes_per_new_block: 30 # override the 30-min default for "new" blocks
```
**New `profile.md` block (optional):**
```markdown
## Time & energy
daily_minutes: 60
sec_per_card: 40
default_energy: normal   # low | normal | high
```
**New method file:** `methods/daily-plan.md`.

### Data & State (what gets written where)
- **`plan-day` writes nothing** — read-only, like `status`/`due`. It reads `TRACK.md` (truth),
  `review-state.json` (due dates), `profile.md`. The plan is a *view*, not persisted state.
- "What got done today" is **not** a new file — it's derived: finishing a block runs the existing
  `grade_card`/`log_entry`, which update `last_active` + `review-state.json` + `registry.json`.
  Avoids a `today-plan.json` that could drift (same reasoning as `registry.json` being rebuildable).
- New frontmatter/profile fields are plain text in existing files; missing → defaults, no migration.

### Prioritization logic (the deterministic core)
`score_block` = a transparent weighted sum (all weights are named constants at module top, tunable,
documented):
```
score = W_deadline * deadline_urgency
      + W_overdue  * overdue_pressure
      + W_goal     * (goal_weight - 1.0)        # neutral at 1.0
      + W_stale    * stale_pressure
      + kind_bias[kind]                          # small fixed nudge per block kind
```
- **deadline_urgency** = `0` if no deadline; else a decaying function of `days_to_deadline`
  (`max(0, urgent_horizon - days_to_deadline) / urgent_horizon`, `urgent_horizon=14`); past-due → 1.0.
- **overdue_pressure** = `min(1.0, max_days_overdue / overdue_cap)` (`overdue_cap=7`) from the oldest
  `due` date among that track's due cards. Distinguishes "12 due today" from "12 due 6 days ago".
- **goal_weight** — user's per-track importance multiplier (default 1.0 neutral); lets the learner
  say "换股重组 matters more than IELTS now" without editing code.
- **stale_pressure** = `min(1.0, (stale_days - stale_threshold) / stale_cap)` once past the
  **N=7-day staleness line the board already computes** (the spec's tunable stale threshold); drives
  `re-anchor` up just enough for a 5-min touch, never enough to outrank a real deadline.
- **kind_bias** — tiny tie-breaker so, all else equal, due `review` (the FSRS safety net) edges out a
  fresh `new` block, and `re-anchor` is lowest. Never large enough to override deadline/goal signals.
- **Determinism guarantee:** no clock reads inside scoring (keys off `--today`), no
  dict-iteration-order dependence (candidates sorted by `(−score, deadline, track_id)`), no model
  involvement. Same inputs ⇒ identical bytes — directly testable.

### Failure modes
- **Nothing active / due / stale** → `scheduled: []`, `total_min: 0`; model offers the lightest
  `new` block as a suggestion, not a forced block.
- **All blocks exceed budget** → everything over budget → `deferred`; the single highest-scored block
  is still surfaced as "if you only do one thing". A within-`urgent_days` deadline block is
  force-scheduled and flagged `budget_exceeded_for_deadline`.
- **Garbage new frontmatter** (non-numeric `goal_weight`) → ignore the bad field, use default, emit a
  `warnings[]` entry; never crash (same posture as "registry stale → rebuild + warn").
- **`review-state.json` missing/corrupt for a track** → due count falls back to "treat as new/due
  now"; the track still gets a review block, plan still renders.
- **Model tries to reorder/invent blocks** → guarded by `methods/daily-plan.md`; verification checks
  rendered order matches engine JSON.
- **Budget=0 or negative `--minutes`** → engine clamps to a 1-block minimum (surface the top block).

### Reuse vs build (explicit)
- **Reuse (already in repo):** `status_board`, `due_cards`, `read_track`, `rebuild_registry`,
  `_days_between`, `_today_str`, `_cards_due_today` in `registry.py`; the `review`/`resume`/`ingest`
  actions for execution; `profile.md` reading already done by `SKILL.md`; FSRS due dates from
  `fsrs.py` (untouched).
- **Reuse (idea-borrow, no code):** **interleaving** and **per-concept mastery gating** from
  DeepTutor — here the interleaving pass, and a future `mastery_gate` reason-code that can suppress a
  `new` block until prerequisite cards are mastered (a designed hook; activated with exam/applied).
- **Genuinely new:** the cross-track candidate-generation + weighted scoring + budget-fitting +
  energy-mapping pipeline (`candidate_blocks` / `score_block` / `plan_day`) and
  `methods/daily-plan.md`. This is the un-filled differentiator; stays engine-deterministic +
  model-narrated, consistent with the spec's "engine keeps state honest; model does pedagogy" split.

### Verification (concrete checks)
- **Unit (stdlib, no pip):** `score_block` — deadline-tomorrow outranks deadline-30-days;
  6-day-overdue outranks same-count due-today; `goal_weight=2.0` outranks `1.0` all else equal.
  `plan_day` determinism — same fixture twice ⇒ byte-equal JSON; permuted `TRACK.md` read order ⇒
  identical ordered output. Budget — `--minutes 20` with three 30-min `new` blocks ⇒ one scheduled +
  two `deferred:over_budget`. Energy — `--energy low` demotes `new` below `review` for a tied pair.
  Deadline override — deadline-tomorrow force-scheduled past a tight budget, flagged. Edges — no
  tracks; bad `goal_weight` (warns, defaults); `--minutes 0` (clamps).
- **Integration (extends the MVP acceptance test):** 3 fixture tracks (deadline in 2 days + 12 cards
  5 days overdue; active with `next_action`, no due; stale 9 days) → `plan-day --today T --minutes 60
  --json` → assert order = [overdue/deadline review, active new, stale re-anchor], `total_min ≤ 60`,
  correct `reason_codes`. Then `review --track <first>`, grade, re-run `plan-day` same `--today` →
  completed review block gone and that track no longer `stale`.
- **Core portability:** `python scripts/registry.py plan-day --today 2026-06-23` runs with no host,
  no pip — precondition for the phase-2 MCP `plan_day` tool.
- **Narration fidelity (manual/eval):** rendered `[PLAN]` order and time-boxes match the engine JSON
  exactly (no reordering, no invented blocks).

### Phase / status
**MVP-adjacent — ship right after the status board lands** (it's the deepening the spec calls for).
Pure additive change to `registry.py` + one method file + optional frontmatter/profile fields — no
breaking changes, no new deps, no migration. The `mastery_gate` reason-code and interleaving tuning
are explicit deferred hooks, activated alongside `exam`/`applied` when per-concept mastery signals exist.

**Open questions:** default weight constants (`W_*`, `urgent_horizon=14`, `overdue_cap=7`,
`sec_per_card=40`, `max_review_block_min=25`) are first-guess — tune during dogfooding. Whether
"today's completed work" should ever be persisted (analytics/streaks) vs. stay derived. Whether energy
should be model-inferred vs. explicit input (kept explicit in MVP for determinism). Interleaving
aggressiveness needs real multi-track data. The `mastery_gate` data source depends on exam/applied.

---

## Engine Hardening (FSRS parity · personalized weights · configurable retention)

### Goal
Close the three engine caveats without adding any runtime dependency, keeping the portable CORE
stdlib-only:
1. **Numeric parity** — turn `fsrs.py`'s "NUMERIC PARITY WITH py-fsrs DEFERRED" header caveat into an
   enforced **dev/CI test oracle**: pin `py-fsrs`, generate a reference grid, assert our scheduler
   matches within tolerance.
2. **Personalized weights** — let a user optionally fit their own FSRS weights (w[0..20]) from real
   review history via `fsrs-optimizer` **offline/opt-in**, loaded as **data** into the unchanged
   stdlib scheduler.
3. **Configurable requested-retention** — make `REQUESTED_RETENTION` (currently hardcoded `0.9`) a
   per-track / global tunable, plumbed through CLI and `TRACK.md` without changing the formulas.

All three are *data + dev tooling* changes; the CORE algorithm (`fsrs.py`) gains no pip import.
`py-fsrs` and `fsrs-optimizer` live only in `requirements-dev.txt` / an opt-in adapter, never
imported by runtime code.

### Logic flow (numbered, end-to-end)

**A. Parity oracle (dev/CI, no runtime dep)**
1. `requirements-dev.txt` pins exactly, e.g. `py-fsrs==<pinned>` (record resolved version + its
   FSRS-6 default weights in a comment so a future bump is auditable).
2. `tests/oracle/gen_fsrs_reference.py` (run manually, **not** CI by default) imports `py-fsrs`,
   sweeps a grid `(rating ∈ {1,2,3,4}) × (elapsed_days ∈ {0,1,3,7,30,180}) × (state ∈
   {new, review-with-prior-state})`, recording `(input_state, grade, now) -> {stability, difficulty,
   interval/due}`.
3. Writes the grid to a **committed JSON fixture** `tests/fixtures/fsrs_reference.json` (CI needs no
   pip install — it reads the committed vectors). Header stores the py-fsrs version + weight vector.
4. CI test `tests/test_fsrs_parity.py` loads the fixture, runs our `schedule()` on each cell, asserts
   each output field within tolerance; also asserts our `DEFAULT_WEIGHTS` equals the py-fsrs FSRS-6
   defaults captured in the header.
5. If parity holds, the misleading "PARITY DEFERRED" sentence in the `fsrs.py` docstring is replaced
   with "parity enforced by tests/test_fsrs_parity.py against py-fsrs==<pinned>".

> **Reconcile-before-trust:** our MVP state machine is intentionally only `new`/`review` (no
> learning/relearning step ladder). py-fsrs models learning steps. The generator MUST drive py-fsrs
> in a mode comparable to our two-state model (compare only the `review`-state stability/difficulty/
> interval math and the new-card seeding); any structurally non-comparable cell is **excluded with a
> documented reason** rather than fudged. The parity test asserts agreement on the subset we
> implement and is explicit about what it does not cover.

**B. Personalized weights (offline, opt-in adapter; CORE stays pip-free)**
1. Review history is logged on every grade (see Data & State → review-log). This is the optimizer's
   input and is written by the existing grade path regardless of whether the user ever optimizes — so
   the data exists when they opt in.
2. The user runs the **optional adapter** `adapters/fsrs_optimize/optimize.py` (its own
   `requirements.txt` pulls `fsrs-optimizer`+torch; documented out-of-CORE, like the Anki/URL
   adapters). It reads `review-log.jsonl` (global, or `--track <id>` for one track), converts to the
   `fsrs-optimizer` input shape, fits weights, and **writes only data**: a `weights.json` (the
   21-float vector + provenance).
3. The adapter does NOT modify `fsrs.py`. It refuses to fit below a minimum review count (default
   400, configurable) and prints the count it had — too-few-reviews is a surfaced limit, not a silent
   bad fit.
4. At runtime, `fsrs.py` loads weights by precedence: **explicit `--weights <path>` → per-track
   `weights.json` → global `weights.json` → built-in `DEFAULT_WEIGHTS`**. `schedule()` already
   accepts `w=`; only CLI/loader wiring is new. Loading is pure-stdlib `json.load`. Malformed or
   not-length-21 → fall back to `DEFAULT_WEIGHTS` and warn (never crash a review).

**C. Configurable requested-retention**
1. `schedule()`/`next_interval()` already take `retention=`; new work is plumbing config → CLI → call
   site.
2. Precedence: **`--retention` CLI → per-track `retention` in `TRACK.md` → global default `0.9`**.
   Validate `0.70 ≤ retention ≤ 0.97`; reject out-of-range with a clear error (mirrors grade
   validation).
3. The `learn` skill's review action passes the resolved retention (and weights path) into `fsrs.py
   schedule`. Lower retention → longer intervals (fewer reviews, more lapses); higher → shorter. The
   one knob a learner tunes for workload vs. recall.

### Components
- **`scripts/fsrs.py`** (existing CORE, stdlib-only) — add: a stdlib `load_weights(path) ->
  list[float] | None` with length/format validation; `--weights` and `--retention` CLI flags on
  `schedule`; retention range validation. No new imports.
- **`requirements-dev.txt`** (new) — pins `py-fsrs==<pinned>`. Dev/CI only.
- **`tests/oracle/gen_fsrs_reference.py`** (new, dev-only) — emits the reference grid fixture.
- **`tests/fixtures/fsrs_reference.json`** (new, committed) — frozen reference vectors + provenance.
- **`tests/test_fsrs_parity.py`** (new) — stdlib-only parity assertions against the committed fixture.
- **`adapters/fsrs_optimize/`** (new, OPTIONAL, out-of-CORE) — `optimize.py` + own `requirements.txt`
  (`fsrs-optimizer`) + `README.md`. Mirrors the established "kept OUT of core" adapter pattern.
- **review-log writer** — a small append helper invoked from the existing `registry.py grade` path,
  appending one JSONL line per graded review.

### Interfaces (CLI subcommands / file formats / method files)
**`scripts/fsrs.py` (extended CLI, stdlib only):**
```
python3 scripts/fsrs.py schedule \
    --state '<json|->' --grade <1|2|3|4> --now YYYY-MM-DD \
    [--retention 0.90] \
    [--weights tracks/<id>/weights.json]
```
- `--retention` (float, default 0.9, validated 0.70–0.97). `--weights` (path; omitted → loader walks
  precedence). Output unchanged (one JSON card-state object), so existing callers + the `learn` skill
  keep working.

**Review-log schema — `review-log.jsonl`** (one object per line, append-only, optimizer-friendly):
```jsonl
{"card_id":"card-0001","track":"share-swap-restructuring","review_date":"2026-06-23","grade":3,"elapsed_days":1,"state_before":"review","stability_before":3.2,"difficulty_before":5.1,"stability_after":7.9,"difficulty_after":5.0,"retention_used":0.9,"weights_source":"default"}
```
Fields let the optimizer reconstruct the (card, ordered-review-sequence, grade, elapsed) tuples and
let a human audit which retention/weights produced each interval.

**`weights.json` (data, loaded by CORE):**
```json
{"weights":[/* 21 floats */],
 "provenance":{"fit_date":"2026-06-23","source_log":"review-log.jsonl",
   "review_count":612,"optimizer":"fsrs-optimizer==<ver>","log_loss":0.31,"scope":"global"}}
```

**`TRACK.md` frontmatter additions (optional, default to global/builtin if absent):**
```yaml
retention: 0.90          # per-track requested retention (0.70–0.97); omit → global default
weights: weights.json    # path (relative to track dir) to personalized weights; omit → global/default
```

**Optimizer adapter CLI (out-of-CORE, opt-in):**
```
python3 adapters/fsrs_optimize/optimize.py \
    [--track <id> | --global] [--min-reviews 400] [--out tracks/<id>/weights.json]
```

### Data & State (what gets written where)
- **`review-log.jsonl`** — written by the grade path. **One global log at repo/vault root**, each
  line carrying `track` so per-track fitting is a filter, not a separate file. Gitignored alongside
  `tracks/` (personal review behavior).
- **`weights.json`** — global at root and/or per-track (`tracks/<id>/weights.json`); both gitignored.
  Only the optimizer writes it, only `fsrs.py` reads it.
- **`retention`** — in `TRACK.md` frontmatter + a global default constant; no new state file.
- **`tests/fixtures/fsrs_reference.json`** — committed (reference math, not personal data).
- `registry.json` cache unaffected (rebuildable). No FSRS schema change to `review-state.json` — the
  review-log is *additive history*, separate from the *current* sidecar state.

### Failure modes
- **py-fsrs not installed in CI** → fine; CI reads the committed fixture, never imports py-fsrs. Only
  `gen_fsrs_reference.py` needs the dep, run manually.
- **Parity drift after a py-fsrs bump** → regenerating the fixture changes committed vectors; the diff
  is the audit trail. If our scheduler then fails tolerance, that's a real signal — don't loosen
  tolerance to hide it.
- **Structural non-comparability (learning steps)** → excluded grid cells documented in the
  generator; parity scope explicit, not silently partial.
- **Too few reviews to optimize** → adapter refuses below `--min-reviews`, prints actual count; no
  `weights.json` written; runtime keeps defaults.
- **Malformed / wrong-length `weights.json`** → `load_weights` returns None + warns; `schedule()`
  falls back to `DEFAULT_WEIGHTS`; review never crashes.
- **Out-of-range `--retention`** → rejected before scheduling (like grade validation), no silent
  clamp that would mislead about workload.
- **review-log append fails (disk/permission)** → warn but do NOT block the grade write to
  `review-state.json`; the log is optimization fuel, not scheduling truth.
- **Personalized weights overfit a tiny/odd history** → provenance (`review_count`, `log_loss`)
  recorded so the user sees the fit's basis; min-review floor guards.

### Reuse vs build (explicit)
- **REUSE — `py-fsrs` (MIT) as dev/CI oracle only.** Pinned in `requirements-dev.txt`, used by
  `gen_fsrs_reference.py` to mint the committed fixture. Never a runtime import.
- **REUSE — `fsrs-optimizer` (BSD-3, pulls torch) in an opt-in offline adapter**, strictly OUT of
  CORE like the Anki/URL adapters. Don't hand-roll torch weight fitting.
- **REUSE — `obsidian-spaced-repetition-recall` JSON-sidecar schema (MIT)** as the conceptual
  reference when shaping `review-log.jsonl` so it stays import/export-friendly.
- **BUILD (genuinely new):** the committed reference-fixture pipeline + stdlib parity test; the
  `review-log.jsonl` writer wired into the existing grade path; the stdlib `load_weights` loader +
  precedence chain; the `--retention`/`--weights` CLI plumbing + validation; the `TRACK.md` fields.
  `schedule()`/`next_interval()` already accept `w=`/`retention=`, so the formula code is **not**
  rewritten — only configured.

### Verification (concrete checks)
- **Parity (CI):** `python3 -m pytest tests/test_fsrs_parity.py` — for every in-scope cell, assert
  `abs(ours.stability - ref.stability) ≤ tol_s` (e.g. `tol_s = max(1e-4, 1e-3*ref.stability)`),
  `abs(ours.difficulty - ref.difficulty) ≤ tol_d` (`1e-4`), `interval` matches exactly. Assert
  `DEFAULT_WEIGHTS == fixture.header.py_fsrs_default_weights`.
- **Fixture regen reproducibility:** rerunning `gen_fsrs_reference.py` against the same pinned py-fsrs
  produces a byte-identical fixture (no timestamps in the vector body).
- **Retention plumbing:** `--retention 0.80` yields a strictly longer interval than `--retention
  0.95` for the same state/grade (monotonicity); `--retention 1.5` exits non-zero; absent flag → 0.9.
- **Weights loader:** valid 21-float file changes output vs. default; 20-float / non-JSON → falls
  back + warns (exit 0, warning on stderr, output equals default).
- **review-log writer:** after grading, exactly one new JSONL line with required keys and correct
  `elapsed_days`/`grade`/`track`; grading still succeeds when the log path is unwritable (warn-only).
- **Optimizer adapter (manual/offline, not CI):** ≥400-line log → length-21 `weights.json` with
  provenance; 10-line log → refuses + prints count. (Excluded from CORE suite; needs torch.)
- **Pip-free CORE invariant:** a CI grep/AST gate proving `scripts/fsrs.py` imports nothing outside
  stdlib + the local loader; `python3 scripts/fsrs.py schedule ...` runs with zero pip installs.

### Phase / status
- **(1) Parity oracle — NOW (MVP hardening).** Dev/CI-only, closes a shipped caveat, zero runtime
  risk (~1 day).
- **(3) Configurable retention — NOW (small).** CLI + frontmatter + one validation; seams already
  exist.
- **(2) Personalized weights — phase 2 (opt-in adapter).** Needs accumulated history; pulls torch →
  out-of-CORE. **But the `review-log.jsonl` writer ships NOW** (with retention work) so history
  accrues from day one.

**Open questions:** exact py-fsrs pin + whether its FSRS-6 defaults match shipped `DEFAULT_WEIGHTS`.
Parity scope boundary (which py-fsrs path is the fair comparison; which cells excluded). Tolerance
values (a real first run confirms whether our math lands inside; if not it's a math bug, not a
tolerance to relax). review-log location (one global file with per-line `track` proposed). min-reviews
floor (400). Retention range (0.70–0.97).

---

## URL → md Ingestion Adapter ("send a link, learn it")

### Goal
Let the user paste ONE link and have learn-everything turn it into a source `.md` inside the target
track's `notes/sources/`, after which the **existing domain tutor-ingest loop** (the `ingest` action
in `skills/learn/SKILL.md`) takes over unchanged. An **optional, out-of-core "ingest adapter"** in
front of domain ingest: it needs network + browser/yt-dlp/OCR, so it is kept OUT of the pip-free
CORE. The contract is deliberately narrow — the adapter's only job is `URL → {source_md_path, title,
metadata}`; the entire downstream pipeline (Map → propose atomic cards → human approves → write
cards/notes/MOC/`review-state.json`) is identical to pasted-text ingest. Closes the product loop:
**link in → learning out.**

### Logic flow (numbered, end-to-end)
1. User invokes `learn` with a URL ("学这个链接 <url>" / "ingest this article <url>") naming or
   implying a target track.
2. The skill resolves the target track (existing `TRACK.md`, or prompt to `create` first) — the
   adapter never creates tracks.
3. **Confidentiality gate (before any fetch):** if the URL host looks internal/login-gated/
   privileged, or the track `mode`/tags mark it confidential (legal tracks), confirm with the user
   that fetching + sending content to the host model is authorized.
4. **Dispatch by URL type** (`classify(url) -> source_type`, see Components). Pick the fetch route.
5. **Fetch attempt (public path first):** run the route's primary fetcher (Crawl4AI/readability,
   yt-dlp subtitles, mineru-ocr, etc.) to produce raw text/markdown + a title.
6. **Login-gated / anti-bot fallback (explicit, not silent):** if the public path returns a
   bot-check, paywall, empty body, or login wall, surface the specific limit and offer the
   logged-in-browser path (`--browser edge` for 抖音/YouTube, a logged-in session for paywalls). If
   neither works, **fail loudly** with the reason and stop — never write a half-empty source file.
7. **Normalize to one `.md`:** clean to markdown, prepend YAML frontmatter (`source_url`, `title`,
   `source_type`, `fetched_at`, `fetcher`, `untrusted: true`), write to
   `tracks/<id>/notes/sources/<slug>-<date>.md`.
8. **DATA_BOUNDARY wrap + injection scan:** wrap the fetched body in `<<<UNTRUSTED_INPUT>>> …
   <<<END_UNTRUSTED>>>` and scan for injection (`ignore previous instructions`, `忽略前面`, hidden/
   zero-width U+200B/U+FEFF, RLO/LRO U+202E/U+202D, ≤1pt/white-on-white). ≥3 red flags → prepend
   `[PROMPT_INJECTION_DETECTED]` and treat the whole body as data, never obeyed.
9. **Return the adapter contract** `{source_md_path, title, metadata}` to the skill.
10. **Hand off to domain ingest unchanged:** the skill feeds `source_md_path` into the normal ingest
    loop. The adapter writes the *source*; only the existing ingest writes the *knowledge base*.

### Components
A single optional adapter (`adapters/url_ingest/` — sibling of `adapters/anki_export/` and
`adapters/fsrs_optimize/`) with one dispatcher + per-type routes that **shell out to existing skills**:

| `source_type` | Primary (public) route — wrap existing skill | Login-gated / anti-bot fallback | Large-doc note |
|---|---|---|---|
| web article / blog | `web-crawl-workflow` (Crawl4AI) or Playwright + readability → md | logged-in browser via `web-stack-router` for paywalls | — |
| 微信公众号 (mp.weixin) | `wechat-article-fetch` (Playwright headless) | — (usually public) | — |
| video — B站 / YouTube / 抖音 | `video-notes` (yt-dlp subtitles → md); fallback audio → `funasr-transcribe` | YouTube bot-check + 抖音 require `--browser edge` | long transcript → hand to [Long-Document Ingestion](#long-document-ingestion-books--large-pdfs) (chunked) |
| PDF link | download → `mineru-ocr`; fallback `case-files-to-md-fast` (local, no upload) | confidential → force local fallback, no cloud upload | if large → hand to [Long-Document Ingestion](#long-document-ingestion-books--large-pdfs) |
| unknown / unsupported | classify fails | — | report unsupported, ask user to paste text |

**Genuinely new code** is only: `classify(url)`, the thin route dispatcher, the frontmatter
normalizer, and the public→login-gated fallback decision logic. Everything that fetches/transcribes/
OCRs is an existing skill wrapped.

### Interfaces (CLI subcommands / file formats / method files)
**Adapter public surface (the stable contract — keep downstream unchanged):**
```
fetch(url: str, track_id: str, *, allow_login=False, prefer_local=False)
    -> { "source_md_path": str,   # tracks/<id>/notes/sources/<slug>-<date>.md
         "title": str,
         "metadata": {
             "source_url": str, "source_type": str, "fetcher": str,
             "fetched_at": ISO8601, "untrusted": true,
             "injection_flagged": bool, "fallback_used": str|null,
             "truncated": bool } }
```
The adapter raises a typed `IngestError(reason, source_type, url)` on bot-check/paywall/empty/
unsupported — never returns a partial file. The skill catches it and reports the explicit limit.

**Source `.md` format** (written to `notes/sources/`, DATA_BOUNDARY-wrapped body):
```markdown
---
source_url: https://...
title: <title>
source_type: web|wechat|video|pdf
fetcher: web-crawl-workflow|wechat-article-fetch|video-notes|mineru-ocr
fetched_at: 2026-06-23
untrusted: true
---
<<<UNTRUSTED_INPUT>>>
<extracted markdown body>
<<<END_UNTRUSTED>>>
```

**Skill wiring:** `skills/learn/SKILL.md` gains a branch in its `ingest` action — "if input is a
URL, call the url_ingest adapter (if installed) to obtain `source_md_path`, then proceed with the
normal ingest loop." No new command; the existing NL `ingest` intent absorbs URLs. **No method file
changes** — pedagogy templates are untouched; the adapter only produces a source to teach from.

### Data & State (what gets written where)
- **Adapter writes exactly one file:** `tracks/<id>/notes/sources/<slug>-<date>.md` (the source).
  Nothing else — no cards, no `review-state.json`, no MOC, no `registry.json`.
- **All knowledge-base writes** (cards/, notes/ Map entry, `plan.md` MOC links, `TRACK.md` log +
  `next_action` + `last_active`, `review-state.json` seeding) happen only in the existing ingest loop,
  only **after human approval** — identical to pasted-text ingest. A pre-approval abort leaves the KB
  unchanged (the orphan source `.md` is the only residue, harmless / re-usable).
- `notes/sources/` lives under gitignored `tracks/`, so scraped/privileged content never enters the
  public repo.
- CORE stays pip-free: the adapter and its deps (yt-dlp, Crawl4AI/Playwright, mineru client) are
  opt-in; `fsrs.py`/`registry.py` never import them.

### Failure modes
- **Bot-check / paywall / login wall** → `IngestError(reason)`; skill surfaces the limit and offers
  the logged-in-browser path; never writes a partial source.
- **Empty / near-empty extraction** (JS-only page, failed OCR) → treated as failure, reported.
- **Unsupported URL type** → classify returns `unknown`; ask the user to paste the text manually.
- **Prompt injection in fetched content** → `[PROMPT_INJECTION_DETECTED]` prepended, body kept as
  DATA inside markers, embedded imperatives never obeyed.
- **Confidential URL** → confirm-before-fetch; PDF/private routes forced local
  (`case-files-to-md-fast`, no cloud upload) when the track is confidential.
- **Large source** (long video transcript, big PDF) → `metadata.truncated`/hand-off to
  [Long-Document Ingestion](#long-document-ingestion-books--large-pdfs) (chunked) rather than dumping
  an unmanageable single file into the tutor loop.
- **Adapter not installed** → skill detects the missing adapter and tells the user to install the
  optional ingest deps, or paste text instead — CORE-only installs degrade gracefully.
- **Network/dependency missing (yt-dlp/Playwright absent)** → clear "this route needs <dep>" error.

### Reuse vs build (explicit)
- **Wrapped, not rebuilt:** `web-crawl-workflow` / `web-stack-router`, `wechat-article-fetch`,
  `video-notes`, `funasr-transcribe`, `mineru-ocr`, `case-files-to-md-fast`, and the existing domain
  `ingest` loop + `methods/*.md` (untouched). The author already owns every fetcher.
- **Genuinely new (small):** `classify(url)`, the route dispatcher, the source `.md` frontmatter
  normalizer, the public→login-gated fallback decision logic, the `IngestError` typed contract, and
  the one-line skill branch. Intentionally thin so the rest of the pipeline is unchanged.
- **Not built:** no new scraper, transcriber, OCR, or card-generation change — pure glue + contract.

### Verification (concrete checks)
- **Contract test:** `fetch()` on a known-public article returns a dict with all required keys, an
  existing `source_md_path`, `untrusted: true`, body wrapped in DATA_BOUNDARY markers.
- **Dispatch test:** `classify()` maps representative URLs (mp.weixin / bilibili / youtube / 抖音 /
  a .pdf link / a blog) to the correct `source_type`.
- **Injection test:** a fixture page with "ignore previous instructions" + zero-width chars yields
  `injection_flagged: true` and a leading `[PROMPT_INJECTION_DETECTED]`; downstream tutor does not
  act on the embedded command (manual/eval).
- **Fallback test:** a simulated bot-check/paywall raises `IngestError` (no partial file) and the
  skill reports the explicit limit.
- **Handoff test (end-to-end, mirrors the spec acceptance test step 2):** url_ingest a sample article
  into a test track → source `.md` exists in `notes/sources/` → the normal ingest loop runs → approve
  3 cards → assert 3 `cards/*.md`, a `notes/` Map entry, `plan.md` MOC links, 3 `review-state.json`
  entries, `TRACK.md` log + new `next_action`. Proves the adapter changes nothing downstream.
- **CORE purity test:** `python scripts/fsrs.py` / `scripts/registry.py` still run with the adapter
  and all its deps uninstalled.

### Phase / status
ROADMAP, **not in MVP** (spec Open Items §"URL → md ingestion"). Schedule after — or alongside —
`exam`/`applied` modes, since it is an isolated adapter touching no engine code. **Spike gate before
building:** confirm yt-dlp + the chosen scraper produce clean md on **1 real article + 1 real
video** (and that the public→login-gated fallback triggers on a known bot-checked URL) BEFORE wiring
the adapter into the skill. If the spike shows poor fetch quality or brittle login paths, ship
pasted-text ingest only and document URL ingest as a known limitation.

**Open questions:** exact repo location (`adapters/url_ingest/` proposed). Whether the adapter shells
out to the existing *skills* (host-mediated, cleaner reuse, couples to host) vs. their underlying
*scripts* (more portable, duplicates setup). Large-source threshold + handoff to Long-Document
Ingestion. Whether to standardize on `--browser edge` + a single logged-in-browser seam across
web/video/PDF. Whether an orphan source `.md` from a pre-approval abort is auto-cleaned or kept.

---

## Long-Document Ingestion (books / large PDFs)

> Scales the `domain` ingest loop from "one short source → propose cards" to "one large work → a
> reading-guide syllabus → a resumable multi-session curriculum." Built as an **optional ingest
> adapter in front of the existing domain ingest** (the same seam the URL adapter uses — and the URL
> adapter **hands large PDFs/transcripts here**). The pip-free CORE (`fsrs.py`, `registry.py`) is
> untouched and every downstream step (tutor teaching, card distillation, FSRS) is reused unchanged.

### Goal
Let a learner say "learn this book" against a 500-page PDF/EPUB and get: (1) a top-down **reading
guide** (what it argues, chapter summaries, a prerequisite/dependency graph, a recommended learning
order, what to extract per chapter) that becomes the track's `plan.md` syllabus; then (2) a
**progressive, resumable curriculum** where each session teaches one context-sized chunk with the
track's pedagogy, distills quality-gated cards with page anchors, and FSRS schedules review — with
the track always recording an exact resumable POSITION (e.g. `ch5 §3`). No step ever re-runs OCR/
extraction (cached), and content larger than one context window is handled by mandatory hierarchical
map-reduce summarization, not truncation.

### Logic flow (numbered, end-to-end)

**Phase A — Intake & extraction (cached, runs once per work)**
1. **Detect source kind.** Invoke ingest with a file path or URL (URL path reuses the
   [URL → md adapter](#url--md-ingestion-adapter-send-a-link-learn-it); output is a local file, then
   identical from here). Sniff type: text-PDF vs scanned/image-PDF (sample N pages, measure
   chars-per-page) vs EPUB vs plain md/txt/docx. Estimate size (pages, bytes, ~tokens = chars/3.5).
2. **Route extraction by kind:** text-PDF → direct text extraction; scanned/image-PDF →
   **`mineru-ocr`** (structured md, tables/formulas/page anchors), **fallback `case-files-to-md-fast`**
   then `case-files-to-md` when MinerU is unavailable/forbidden/confidential; EPUB → unzip XHTML
   spine → md; md/txt/docx → passthrough / `md2word`-family read.
3. **Wrap as UNTRUSTED (DATA_BOUNDARY).** All extracted text wrapped `<<<UNTRUSTED_INPUT>>>…
   <<<END_UNTRUSTED>>>`, scanned for injection; ≥3 red flags → prepend `[PROMPT_INJECTION_DETECTED]`
   and never obey embedded imperatives (same rule the short-article ingest applies).
4. **Cache the raw extraction** to `notes/sources/_raw/<work-id>.md` + a manifest keyed by **content
   hash of the source file**. On any future ingest of the same file, skip Phase A if the hash matches
   — OCR/extraction never re-runs.

**Phase B — Structural split (book → chapters → sections → chunks)**
5. **Detect TOC / structure.** Prefer real structure: PDF bookmarks/outline, EPUB nav, or a
   "Contents" page; else **heuristic fallback** (markdown heading levels from OCR; if absent, segment
   by font-size jumps MinerU preserved, else length windows + "Chapter N / 第N章" regex). Record
   `structure_source: toc|bookmarks|headings|heuristic`.
6. **Build a hierarchy** book → chapter → section → **context-sized chunk** (~6–8k tokens/chunk,
   configurable). Preserve heading hierarchy and **page anchors** on every node (`p.123–145`).
   Figures/tables kept as captioned `[figure: …]` / `[table: …]` placeholders with page anchor;
   never fabricate content.
7. **Persist the structure map** to `notes/sources/<work-id>.structure.json` (the chunk index the
   session picker reads).

**Phase C — 导读 / reading-guide pre-pass (top-down map BEFORE deep study)**
8. **Hierarchical map-reduce summarization** (mandatory — this is how it scales past one context
   window): *Map:* each chunk → ~150-word gist + key terms. *Reduce L1:* fold chunk gists → chapter
   summary + that chapter's prerequisites and what it introduces. *Reduce L2:* fold chapter summaries
   → the book's **central argument**, a **prerequisite/dependency graph**, a **recommended learning
   order** (may differ from page order), with **"what to extract per chapter"** (objective + target
   card count).
9. **Emit the reading guide as a proposed `plan.md`** (syllabus / MOC): thesis, chapter-by-chapter
   table, dependency graph (mermaid + `[[wikilinks]]`), recommended order, per-chapter extraction
   targets. Present for **human approval** (same human-in-the-loop gate as card writes). The learner
   may edit order/scope before accepting.
10. **On approval:** write `plan.md`, per-chunk source notes `notes/sources/<work-id>/<chunk-id>.md`,
    set `TRACK.md` `next_action` to the first chunk in the recommended order, and write
    `curriculum.json` (`position`, ordered chunk list, per-chunk status `pending`). Nothing is
    written before approval (abandon = track unchanged).

**Phase D — Progressive learning (multi-session curriculum)**
11. **Session start (`resume`):** read `TRACK.md` + `curriculum.json` → pick the **next chunk** =
    first chunk in recommended order whose status is `pending` and whose prerequisite chunks are
    `taught` (prereq gate; falls back to recommended order if prereqs unsatisfiable). "Resume" jumps
    straight to `position`.
12. **Teach the chunk** using the track's `methods/<pedagogy>.md` (tutor read-along + silent
    `learner-model.md`), grounded only in that chunk's source note + the chapter summary as context
    (never the whole book).
13. **Distill cards per chunk through the quality gate** (L1/L2/L3 layering + atomicity +
    duplicate-check + refusal-to-atomize-proofs). Each card stores a **page-anchor backlink**
    (`source: <work-id> p.137`) and `chunk: <chunk-id>`.
14. **Human approves cards** → write `cards/*.md`, seed FSRS state in `review-state.json`, append to
    `notes/`, mark chunk `taught`, advance `position`, update `TRACK.md` log + `last_active` +
    `next_action`. FSRS then schedules these into the normal cross-track `review`.
15. **Repeat** session-by-session until all chunks `taught`; `review` runs across the whole book's
    cards like any other track.

### Components
- **`scripts/ingest_doc.py` (NEW, OPTIONAL ADAPTER — OUT of pip-free core; lives under `adapters/`)**
  — orchestrates Phases A–B: detect kind, dispatch extraction to wrapped skills, cache by hash, build
  + persist the structure map. May need pip/network/OCR deps.
- **`scripts/structure.py` (NEW, stdlib-only — CAN live in core)** — pure functions: parse TOC/
  bookmarks, heuristic heading/length split, build the chunk hierarchy with page anchors, read/write
  `structure.json` + `curriculum.json`, and the **prereq-gated session next-chunk picker**. No
  external-dep I/O → portable, testable standalone.
- **Reading-guide pre-pass** — not new code; a host-model procedure driven by a **NEW
  `methods/reading-guide.md`** (hierarchical map-reduce instructions + the `plan.md` output shape).
  The model executes it; `structure.py` supplies the chunk index it iterates.
- **`skills/learn/SKILL.md` (EXTENDED)** — add a "large work" branch to the `ingest` intent: if the
  source exceeds a size threshold (> ~30k tokens or > ~30 pages), route through `ingest_doc.py` +
  `reading-guide.md` instead of the single-shot short-article ingest; add the curriculum-aware
  `resume` (next-chunk pick).
- **Existing reused unchanged:** `scripts/fsrs.py`, `scripts/registry.py`,
  `methods/{tutor,socratic,feynman,active-recall,learner-model}.md`.

### Interfaces (CLI subcommands / file formats / method files)
**Skill surface (natural language, no new commands):**
- "learn this book: <path|url>" → large-work ingest (Phases A–C), ends at reading-guide approval.
- "approve the plan" / edits → writes `plan.md` + curriculum (Phase C step 10).
- "continue <track>" / "resume" → next-chunk session (Phase D). "review" → unchanged, cross-track FSRS.

**Adapter CLI (`adapters/.../ingest_doc.py`, opt-in):**
```
python3 ingest_doc.py extract <file|url> --track <id>   # Phase A, cached by hash
python3 ingest_doc.py split   <work-id>  --track <id>   # Phase B → structure.json
```
**Core CLI (`scripts/structure.py`, stdlib):**
```
python3 scripts/structure.py next-chunk <track>                 # prereq-gated session picker
python3 scripts/structure.py mark <track> <chunk-id> taught
```
**Method file (NEW):** `methods/reading-guide.md` — map-reduce summarization + `plan.md` schema.

**New file formats:**
- `notes/sources/_raw/<work-id>.manifest.json` — `{source_path, sha256, kind, pages, est_tokens,
  extractor, extracted_at}` (cache key).
- `notes/sources/<work-id>.structure.json` — hierarchy `{book, chapters:[{title, page_range,
  sections:[{title, page_range, chunks:[{chunk_id, page_range, est_tokens, figures:[], tables:[]}]}]
  }], structure_source}`.
- `tracks/<id>/curriculum.json` — `{work_id, position:"ch5/§3/chunk-0042", order:[chunk_id…],
  chunks:{<chunk_id>:{status:"pending|taught", chapter, prereqs:[chapter…], cards:[card-id…]}}}`.
- Card frontmatter gains `source: <work-id>` + `page: 137` + `chunk: chunk-0042` (Obsidian-compatible
  backlink).

### Data & State (what gets written where)
- **book → one `domain` track** (`tracks/<id>/`).
- **chapters/sections → `plan.md`** (the approved reading guide / MOC) + the `structure.json` index.
- **per-chunk source text → `notes/sources/<work-id>/<chunk-id>.md`**; raw extraction cached in
  `notes/sources/_raw/`.
- **position + reading-guide-driven order → `curriculum.json`**; the resumable position is **mirrored
  into `TRACK.md` `next_action`** (human-readable, e.g. `读 ch5 §3，产出≤4张卡`). **`curriculum.json`
  `position` is canonical (machine source of truth); `TRACK.md` `next_action` is the derived
  human-readable view** — consistent with the registry-cache rule.
- **cards → `cards/*.md`** with page-anchor backlinks; **FSRS state → `review-state.json`** (engine
  unchanged). `registry.json` cache updated with `cards_total`; rebuildable from `TRACK.md`.
- All of `tracks/`, raw extractions, and source notes are **gitignored**.

### Failure modes
- **OCR garbage** → after extraction, a quality heuristic (dictionary-word ratio / non-CJK noise);
  below threshold → warn, mark `extractor_low_confidence`, suggest re-run with `case-files-to-md`
  (higher-precision local) before building the guide; never silently teach garbage.
- **Content > context** → **mandatory hierarchical map-reduce** (Phase C step 8); never truncate a
  chunk/chapter to fit — if a single chunk still overflows, `structure.py` re-splits it smaller.
- **No TOC / no bookmarks** → heuristic split; record `structure_source: heuristic`, warn the guide
  is approximate, ask the user to confirm/adjust chapter boundaries at approval.
- **Mixed scanned+text PDF** → per-page routing; manifest records per-range extractor.
- **Math/tables/figures** → captioned placeholders with page anchors; referencing cards get a "see
  source p.X" note; never fabricate figure content; refusal policy declines to atomize proofs/worked
  examples.
- **Copyright / personal-use** → local fair-use/personal-learning only; raw text stays gitignored;
  README states scope; confidential works require explicit confirm-before-send.
- **Huge token cost** → at size detection, **show an estimate and let the user pick scope** (whole
  book vs named chapters vs "first 3 chapters"); map-reduce is cheaper than teaching, so the guide is
  produced before committing to full per-chunk teaching; `curriculum.json` lets the user stop after
  any chunk.
- **Re-ingesting a changed file** → hash mismatch → re-extract; hash match → reuse cache.
- **User abandons before plan approval** → nothing written beyond the (reusable) cache; track
  unchanged (matches existing ingest atomicity).

### Reuse vs build (explicit)
- **REUSE (wrap):** `mineru-ocr` (scanned→md, anchors); `case-files-to-md-fast` / `case-files-to-md`
  (local fallback, confidential/offline); the [URL → md adapter](#url--md-ingestion-adapter-send-a-link-learn-it)
  for URL sources; the domain tutor loop (`methods/tutor.md` + `learner-model.md`), the card-quality
  L1/L2/L3 rubric, `scripts/fsrs.py`, `scripts/registry.py` — all unchanged.
- **BUILD (genuinely new):** the **structural split + chunk hierarchy with page anchors**
  (`structure.py`); the **导读 reading-guide map-reduce pre-pass** (`methods/reading-guide.md`)
  producing an approved `plan.md`; the **resumable curriculum + prereq-gated session picker**
  (`curriculum.json` + next-chunk logic); the **size-detection/scope-picker + extraction cache**
  (`ingest_doc.py`). This is the project's differentiator extended to "a book is a curriculum", which
  no surveyed project does.

### Verification (concrete checks)
- **Unit (`structure.py`, stdlib, no host/pip):** a fixture md with `# / ## / ###` + a fake TOC →
  expected chunk hierarchy with correct page ranges; no-heading fixture → length-window split;
  next-chunk picker returns the first `pending` chunk whose prereqs are `taught`, falls back to
  recommended order when prereqs unsatisfiable; `mark taught` advances `position`.
- **Cache test:** ingest the same fixture twice → second run reports `cache hit`, does not invoke the
  extractor (assert via a stub call-count).
- **Map-reduce scaling (eval):** on a multi-chapter fixture exceeding one context window, the guide is
  produced without any single LLM call receiving the whole book (assert each map call's input ≤ chunk
  budget); guide contains thesis + per-chapter summary + dependency graph + recommended order +
  extraction targets.
- **Integration (acceptance):** `learn this book <sample 60-page PDF>` → cached extraction +
  `structure.json`; approve guide → `plan.md` + `curriculum.json` (all `pending`); `resume` → teaches
  chunk-0001, approve 3 cards → 3 `cards/*.md` with page anchors, 3 `review-state.json` entries,
  chunk-0001 `taught`, `position` advanced, `TRACK.md` log updated; `status` shows the book track with
  `cards_total: 3` and next-chunk action; second `resume` picks chunk-0002.
- **DATA_BOUNDARY:** an injected line + zero-width chars → `[PROMPT_INJECTION_DETECTED]` flagged,
  imperative not obeyed.
- **Core portability preserved:** `structure.py` runs standalone (no pip); `ingest_doc.py` is absent
  from CORE import paths — `python3 scripts/fsrs.py` / `registry.py` still run with zero installs.

### Phase / status
**Post-MVP, scheduled alongside / just after `exam`/`applied` and the URL→md adapter** (shares the
same "optional ingest adapter in front of domain ingest" seam). Build order: (1) `structure.py` +
`methods/reading-guide.md` against an already-extracted md (no OCR dep) to prove guide + curriculum +
session picker; (2) wire `ingest_doc.py` extraction/cache wrapping `mineru-ocr` & fallbacks; (3)
spike a real 300–500-page book end-to-end and confirm token budgeting + scope-picker before declaring
"learn a book" supported.

**Open questions:** chunk-budget default (~6–8k tokens vs auto-scale to a fraction of the host context
window). Mastery-gate strength for next-chunk progression (prereq-graph + FSRS due only, vs a
DeepTutor-style demonstrated per-concept check — needs a mastery signal not yet in the data model).
OCR-quality heuristic threshold (needs calibration on a real scanned book). Whether a book's `plan.md`
reuses the accumulating-domain MOC schema or a distinct 'finite syllabus' variant the status board can
show as progress = chunks taught / total.

---

## Exam Mode

> A track type for learning with a **defined endpoint and a scored target** (IELTS band 7, AWS-SAA
> pass, 司法考试). Unlike `domain` (open-ended accumulation), `exam` is **syllabus-driven**: a fixed
> module list to cover, a deadline to race, and a readiness estimate ("are you on track to hit the
> score by the date?"). Borrows claude-tutor's diagnostic → plan → study → quiz → review loop and
> layers DeepTutor-style per-module mastery gating on top of the existing FSRS net.
>
> Status: **deferred in MVP** (spec §Non-Goals); designed here to slot into the spine with zero engine
> rewrite. The author's private `ielts-*` skills are used only as a **WRAP example** — exam mode never
> depends on them.

### Goal
Let one person drive a scored, deadline-bound credential the same way they drive a domain track —
under the same status board, the same `learn` skill, the same FSRS engine — while adding the three
things `domain` lacks: (1) a **syllabus** of modules to cover, (2) **per-module mastery + a single
readiness estimate** toward a target score, and (3) **mock-exam recording** so practiced/simulated
scores feed both FSRS and the readiness number. The differentiator vs. just using IELTS skills: exam
mode is **generic** (any cert, any syllabus) and lives in the cross-track OS, so "IELTS + AWS cert +
法考" coexist on one board.

### Logic flow (numbered, end-to-end)
1. **create (exam)** — `learn` create with `mode: exam`. Asks: title, **target score** (free-form
   string + numeric), **exam date** (deadline, required for exam — not optional), pedagogy (default
   `socratic` for study, `active-recall` for review), and a **syllabus** from one of: (a) a built-in
   template (`syllabus/<exam>.md`), (b) a wrapped skill that emits one, (c) the user pasting module
   names. Scaffolds the folder, writes `TRACK.md` (with exam fields) + `syllabus.md` + initializes
   `exam-state.json`.
2. **diagnostic** — first action after create (claude-tutor's diagnose-first). The host model runs a
   short diagnostic per module (probe questions / a baseline mini-mock) to seed an initial `mastery`
   0.0–1.0 per module. No cards yet — calibration. Recorded as a `diagnostic`-kind entry in `mocks/`,
   seeds module mastery + a first **readiness**.
3. **plan** — `scripts/exam.py plan` reads `syllabus.md` + `exam-state.json` + days-to-deadline and
   produces a **study order**: weakest-mastery, highest-weight, not-yet-covered first, pruned to fit
   remaining days. Writes a refreshed `next_action` into `TRACK.md`. The exam analogue of domain's
   `next_action`.
4. **study (one module)** — runs the track's `methods/<pedagogy>.md` loop **scoped to one syllabus
   module**. Cards proposed + human-approved + written exactly as in domain ingest (reuses the domain
   card path verbatim), but each card is tagged `module:<id>` so mastery can be attributed. On
   approval, FSRS state seeded; the module's `covered` flag is set.
5. **quiz (one module)** — `active-recall` over that module's due cards **plus** generated exam-format
   items. Grades feed FSRS AND update the module's mastery via a rolling accuracy. A module crossing a
   threshold sets `mastered: true` — the **mastery gate** that lets `plan` stop re-surfacing it.
6. **mock (full or section)** — record a full/sectional mock: per-module/per-section raw scores + a
   converted overall, with mandatory `source` tagging (`real_exam` > `official_practice` >
   `self_estimate`). Written to `mocks/`. A mock recalibrates module mastery (mock evidence outranks
   card accuracy) and recomputes **readiness**.
7. **review** — unchanged from the spine: `learn review` collects due cards across all tracks;
   exam-track cards participate identically. Exam mode adds nothing to the review engine.
8. **status** — the cross-track board shows exam tracks with extra columns derived from
   `exam-state.json`: target vs. latest mock, days-to-exam, **readiness %**, # modules mastered /
   total. Flags `behind-schedule` when readiness trails the linear ramp to target by date.

### Components
1. **`scripts/exam.py` (NEW, stdlib only)** — the exam engine beside `fsrs.py`/`registry.py`: reads/
   writes `syllabus.md` + `exam-state.json` + `mocks/*.json`, computes module mastery roll-up and the
   readiness estimate, produces the study plan. Zero pip deps, zero host coupling (becomes MCP tools
   later).
2. **`methods/diagnostic.md` (NEW pedagogy template)** — the diagnose-first calibration turn. A data
   file like the existing `methods/*.md`; no engine change.
3. **`syllabus/<exam-id>.md` (NEW, optional shipped templates)** — generic, non-personal module lists
   for common exams (the repo ships a couple; users add their own). Per-track copy lands at
   `tracks/<id>/syllabus.md`.
4. **Existing, reused unchanged:** `scripts/fsrs.py`, `scripts/registry.py`,
   `methods/{tutor,socratic,feynman,active-recall,learner-model}.md`, `skills/learn/SKILL.md`.

### Interfaces (CLI subcommands / file formats / method files)
**New `scripts/exam.py` subcommands** (mirror registry.py's argparse style — JSON to stdout):
```
exam.py init-syllabus  --track <id> --from <template-id|-|path>   # write syllabus.md + seed exam-state.json
exam.py set-target     --track <id> --score "<raw>" --scale "<lo-hi>" --exam-date YYYY-MM-DD
exam.py plan           --track <id> --today YYYY-MM-DD            # -> {study_order:[module...], next_action, behind_schedule}
exam.py mastery        --track <id>                               # -> per-module {mastery, covered, mastered} + overall
exam.py record-mock    --track <id> --kind <full|section|diagnostic> \
                       --source <real_exam|official_practice|self_estimate> \
                       --scores '<json {module|section: raw}>' --overall <num> \
                       --date YYYY-MM-DD --note "<...>"           # writes mocks/<date>-<kind>.json, recalibrates
exam.py readiness      --track <id> --today YYYY-MM-DD            # -> {readiness:0..1, projected_score, target, on_track}
```
Card mastery attribution reuses **registry.py `add-card --tags`**: exam study tags every card
`module:<module-id>` so `exam.py mastery` groups FSRS grades by module — no new card schema, just a
tag convention. `exam.py` reads `review-state.json` (FSRS sidecar, **read-only**) for recent grades;
it never writes scheduling state (one authoritative FSRS writer = `fsrs.py`). `registry.py
create-track` already takes `--mode`/`--pedagogy`/`--deadline` — exam reuses it with `--mode exam
--deadline <exam-date>`; `init-syllabus`/`set-target` run immediately after.

**`learn` skill surface (NL intents, no new commands):** "start exam prep / 备考", "diagnose me",
"what should I study", "quiz me on <module>", "record my mock / 录模考分", "am I ready / readiness".
Dispatches to `exam.py` + the relevant `methods/*.md`. **`methods/diagnostic.md`** auto-selected for
the create→diagnostic step.

### Data & State (what gets written where)
**`TRACK.md` — exam adds frontmatter fields** (domain ignores them; the field set stays a superset so
registry.py's parser/rebuild keeps working — new keys are passed through):
```markdown
---
id: ielts-2026
title: IELTS Academic
mode: exam                 # NEW value for the existing mode field
pedagogy: socratic
status: active
created: 2026-06-23
deadline: 2026-09-15       # = exam date (required for exam mode)
last_active: 2026-06-23
next_action: 诊断完成；先攻写作 Task 1（mastery 0.2）
# --- exam-mode-only fields ---
target_score: "7.0"
score_scale: "0-9"
syllabus: syllabus.md
---
```
**`tracks/<id>/syllabus.md` (NEW)** — module list + weights (markdown, human-editable):
```markdown
# Syllabus — IELTS Academic
| module_id | title           | weight | exam_section |
|-----------|-----------------|--------|--------------|
| listening | Listening       | 0.25   | Listening    |
| reading   | Reading         | 0.25   | Reading      |
| writing-t1| Writing Task 1  | 0.10   | Writing      |
| writing-t2| Writing Task 2  | 0.15   | Writing      |
| speaking  | Speaking        | 0.25   | Speaking     |
```
**`tracks/<id>/exam-state.json` (NEW, rebuildable derived state like review-state.json)** — per-module
mastery + running readiness; rebuildable from `syllabus.md` + `mocks/*.json` + `review-state.json`:
```json
{ "target": {"score": "7.0", "scale": "0-9", "exam_date": "2026-09-15"},
  "modules": {
    "writing-t1": {"weight": 0.10, "covered": true, "mastery": 0.34,
                   "mastered": false, "card_count": 8, "last_mock_score": 5.5} },
  "readiness": 0.41, "projected_score": "6.0", "computed_at": "2026-06-23" }
```
**`tracks/<id>/mocks/<date>-<kind>.json` (NEW)** — one file per recorded mock/diagnostic:
```json
{ "date": "2026-06-23", "kind": "full", "source": "official_practice",
  "scores": {"listening": 6.5, "reading": 6.0, "writing-t1": 5.5, "writing-t2": 6.0, "speaking": 6.5},
  "overall": 6.0, "note": "Cambridge 18 Test 2" }
```
**Mastery roll-up rule** (in `exam.py`, deterministic): per module `mastery = clamp(
0.5*card_accuracy_recent + 0.5*normalized_last_mock )`, where `card_accuracy_recent` = good/easy
fraction over that module's recent FSRS grades and `normalized_last_mock = raw/scale_hi`; a module
with a mock uses the mock as the stronger signal, a module with only cards falls back to card
accuracy. `mastered = mastery >= 0.8` (tunable). **Readiness** = `sum(weight_i * mastery_i)`;
`projected_score = readiness * scale_hi`; `on_track` compares readiness to the linear ramp
`elapsed/total_days`. All thresholds are constants in one place. `registry.json` gains exam fields
(`target_score`, `exam_date`, `readiness`) so the board renders without opening each TRACK.md — still
rebuildable.

### Failure modes
- **No deadline on exam create** → reject (readiness math undefined without it). Domain stays
  deadline-optional.
- **Mock with unknown module/section id** → `record-mock` warns + records under an `unmapped` bucket,
  does not crash; mastery ignores unmapped scores.
- **Mock missing `source`** → reject (mandatory; prevents a self-estimate masquerading as a real
  score).
- **`exam-state.json` missing/corrupt** → `exam.py` rebuilds it from `syllabus.md` + `mocks/*` +
  `review-state.json`; warn.
- **`syllabus.md` empty / unparseable** → block plan/mastery with a clear error; never silently treat
  as zero modules.
- **Exam date passed** → board flags `exam-overdue`; does not auto-archive (matches domain).
- **Readiness over-claiming from thin data** → a module with neither a mock nor enough grades is
  marked `low-confidence` and excluded from `on_track` optimism (report readiness with a "n modules
  uncalibrated" caveat rather than a falsely high number).
- **Untrusted study material (DATA_BOUNDARY)** → identical to domain ingest; pasted past-papers are
  DATA, scanned for injection.
- **Confidential / paid exam content** → README note: do not ingest copyrighted exam material you
  can't lawfully use; `tracks/` gitignored.

### Reuse vs build (explicit)
- **REUSE (spine, unchanged):** `scripts/fsrs.py` (all scheduling — exam adds zero scheduling code),
  `scripts/registry.py` (`create-track`/`add-card`/`status`/`log`/due/grade — exam cards flow through
  the existing card path), `methods/{tutor,socratic,feynman,active-recall,learner-model}.md`, the
  single `learn` skill.
- **REUSE (pattern, from research):** claude-tutor's **diagnostic → plan → study → quiz → review**
  loop; DeepTutor's **per-concept mastery gate** as the module-mastery threshold; ielts-mock's
  **source-of-truth tagging** for mock records.
- **WRAP example (NOT a dependency) — the author's private `ielts-*` skills:** exam mode is the
  generic engine; the IELTS suite can plug in as an *optional adapter* without exam mode importing it.
  Interop seams: (1) **syllabus producer** — `ielts` skill emits an IELTS `syllabus.md`; exam mode
  consumes it via `init-syllabus --from -`. (2) **mock importer** — point `record-mock` at the
  directories `ielts-mock` already writes (`02_模考记录/`) and the IELTS band-scale. (3) **study
  delegation** — for an IELTS exam track, the `learn` skill MAY hand a study turn to
  `ielts-writing`/`ielts-reading` for domain-expert coaching, then record cards + mastery back. **None
  required**: with the ielts skills absent, exam mode runs fully on shipped/pasted syllabi and manual
  mocks. The dependency arrow points one way (ielts → exam-state files), so the open-source product
  never ships private skills.
- **GENUINELY NEW (build):** `scripts/exam.py`, `methods/diagnostic.md`, the `exam-state.json` +
  `syllabus.md` + `mocks/*.json` formats, the exam frontmatter fields, and the exam intents in `learn`.

### Verification (concrete checks)
- **Unit (`scripts/exam.py`, stdlib harness):** `mastery` roll-up — fixture syllabus + a mock + a
  stub review-state → expected per-module mastery and overall readiness within tolerance; `mastered`
  flips at the threshold and not before. `readiness` math — `sum(weight*mastery)` matches by hand;
  weights not summing to 1.0 are normalized (or rejected) deterministically. `plan` — weakest×
  highest-weight×uncovered first, pruned to the day budget; `behind_schedule` true when readiness <
  ramp. `record-mock` — missing `source` rejected; unknown module → `unmapped` + warning;
  exam-state recomputed. **Rebuild** — delete `exam-state.json`, rerun `mastery` → identical state
  reconstructed (proves it's a cache).
- **Integration (end-to-end):** create exam track (target `7.0` / scale `0-9` / exam date) → valid
  `TRACK.md` (mode exam, deadline) + `syllabus.md` + seeded `exam-state.json`; registered. Diagnostic
  → `mocks/<date>-diagnostic.json`, mastery + first readiness seeded. Study a module → approve cards
  (tagged `module:writing-t1`) → cards in `cards/`, FSRS state seeded, module `covered`. Quiz, grade →
  FSRS due dates advance AND module mastery rises. `record-mock --kind full --source
  official_practice` → readiness + projected_score recompute; `behind_schedule`/`on_track` reflect the
  date. `status` → exam track shows target vs. latest mock, days-to-exam, readiness %, mastered/total.
- **Core portability:** `python3 scripts/exam.py plan/mastery/readiness ...` runs standalone, no host,
  no pip.
- **Wrap (IELTS interop, manual):** point `init-syllabus`/`record-mock` at IELTS-skill outputs where
  they exist → exam-state populates; without them the same exam track still creates and runs from a
  shipped/pasted syllabus + manual mocks (proves no hard dependency).

### Phase / status
**Phase 2** (post-MVP). Unblocked once the spine contract is proven by domain; adds only
`scripts/exam.py`, `methods/diagnostic.md`, three new file formats, and exam intents — no change to
`fsrs.py` scheduling or the registry card path. Sequence before or alongside `applied`; the IELTS WRAP
can land later as an optional adapter.

**Open questions:** mastery threshold (0.8) and the card-accuracy vs mock 50/50 blend are first-guess
constants — tune against real data. Readiness as `sum(weight*mastery)*scale_hi` is a linear proxy;
real exams (IELTS band conversion, pass/fail certs) are non-linear — may need a per-exam
score-conversion function in the syllabus template. Whether exam study delegates whole turns to
wrapped domain-expert skills by default or only on request. Whether `mocks/` should be JSON
(engine-friendly, chosen) or markdown (Obsidian-friendly like cards/notes). Which generic syllabi are
safe to ship vs. user-supplied only (licensing).

---

## Applied Mode (learn-by-building)

### Goal
Let the learner master a skill by **doing a real project** (building an LLM agent, shipping a CLI,
learning a framework) while learn-everything captures the learning as a *byproduct*: the tutor pairs
on the actual work, and after each work session distills what was learned, the gotchas/traps hit, and
concepts that surfaced into the **same** atomic cards + notes the `domain` mode produces — all fed
into the **same FSRS engine**. Where `domain` is source-driven (read → cards) and `exam` is
syllabus-driven (cover the spec), `applied` is **task/project-driven**: progress is measured in
shipped milestones, and durable knowledge is the residue of solving real problems. The only mode whose
triggering event is "I worked on my project," not "I read something" or "I have a test."

### Logic flow (numbered, end-to-end)
1. **Pick project** — `create` a track with `mode: applied`. The skill asks for: project goal (one
   sentence), an optional deadline, the pedagogy (default `worked-example`; `socratic`/`feynman`
   selectable). Scaffolds `tracks/<id>/` with an applied-flavored `TRACK.md` plus `milestones.md` and
   `worklog.md`.
2. **Decompose into milestones** — the tutor (host model, following `methods/worked-example.md` +
   `methods/learner-model.md`) helps break the goal into 3–7 ordered, demonstrable milestones (each
   ending in a runnable/observable artifact). Written to `milestones.md` as a checklist; the first
   becomes `current_milestone` and `next_action`. **No cards/notes written here** — planning only.
3. **Work session (pairing)** — `resume` reads `TRACK.md` → `current_milestone` + `current_blocker`.
   The tutor pairs on the real task: surfacing concepts *just-in-time* ("you're about to need a retry
   loop — do you know why naive retries fail here?"), withholding answers per pedagogy, silently
   updating its learner-model. The learner does the actual building in their own editor/repo
   (learn-everything does not own the project code). Friction, dead-ends, "aha" moments noted in
   `worklog.md` as they happen (append-only scratch; untrusted-content rules apply if code/errors are
   pasted).
4. **Distill (the byproduct step)** — when the learner says a session is done (or a milestone is
   hit), the skill runs the **applied distillation loop**: it reads the session's `worklog.md` delta +
   the dialogue and proposes three buckets — (a) **concepts learned**, (b) **traps/gotchas** (the
   mistakes actually hit + the fix — highest-value cards, framed "symptom → cause → fix"), (c)
   **notes** (what was built + why, linked into `plan.md` MOC). Applies the **card-quality gate**
   (L1/L2/L3, atomicity, dedup, refusal-to-atomize-whole-procedures — the same rubric `domain` uses).
5. **Human approval** — exactly as `domain`: the learner approves which cards enter the knowledge
   base. **Nothing is written until approval.**
6. **Commit on approval** — write approved cards to `cards/` (tagged with the milestone + `#trap`
   where applicable), append the distilled note to `notes/`, update `plan.md` MOC wikilinks, seed FSRS
   state in `review-state.json`, append a `worklog.md`/`TRACK.md` Log row, and advance state: mark
   milestone done in `milestones.md` if reached, set new `current_milestone` + `current_blocker` +
   `next_action` + `last_active`.
7. **Next milestone** — loop back to step 3 until all done → `status: done`. Cards from earlier
   milestones keep surfacing in cross-track `review` along the way (the safety net runs continuously).

### Components
- **No new skill.** Applied mode is a branch *inside* the existing single `learn` skill, selected by
  the track's `mode: applied` frontmatter — same as `domain`. The skill's `create` / `resume` /
  `distill` / `review` intents read `mode` and load the right method file + write the right files.
- **New method file `methods/worked-example.md`** (pedagogy — data, not code): the applied-default
  teaching template. Encodes just-in-time concept surfacing, "make them try the build step before
  explaining," the worked-example→completion-problem→independent-problem fade, and a milestone-mastery
  check before advancing. Already named as a first-class pedagogy in the spec's axis list, so this
  fills a planned slot.
- **Reuses** `methods/learner-model.md` (silent per-turn state inference) and `methods/socratic.md` /
  `methods/feynman.md` unchanged (selectable as the applied track's pedagogy).
- **Engine: zero new code.** `scripts/fsrs.py` and `scripts/registry.py` used as-is. Applied cards are
  ordinary cards; applied tracks are ordinary registry rows.

### Interfaces (CLI subcommands / file formats / method files)
- **Command surface:** unchanged — the same `learn` skill, NL intents. `create` gains a `mode:
  applied` path; a new **`distill`** intent ("I'm done for today" / "wrap up this session" / "what did
  I learn") triggers the byproduct loop. `resume`/`review`/`status` are mode-agnostic.
- **`registry.py`:** no signature change. `mode` is already a registry field. Applied tracks surface
  `next_action` (= current milestone step) and `cards_total` like any track. Optional additive: the
  status board may show `M2/5` milestone progress derived from `milestones.md` (display-only read;
  registry.json stays rebuildable).
- **`fsrs.py`:** no change. Same `schedule(card_state, grade, now)`.
- **New method file:** `methods/worked-example.md` (the only genuinely new file).
- **New per-track files:** `milestones.md` (ordered checklist) and `worklog.md` (append-only scratch).

**`TRACK.md` applied-mode fields** (superset of the `domain` frontmatter — same file, extra keys;
unknown keys harmless to `domain`/`exam`):
```markdown
---
id: build-llm-agent
title: Build an LLM coding agent
mode: applied              # domain | exam | applied
pedagogy: worked-example   # default for applied; socratic | feynman selectable
status: active
created: 2026-06-23
deadline: null
last_active: 2026-06-23
next_action: 实现工具调用循环，先让它能跑通一次 read_file
project_goal: A CLI agent that can read/edit files and run bash, with a tool-use loop
current_milestone: M2 - tool-calling loop          # mirrors the active item in milestones.md
current_blocker: 模型偶尔返回非法 JSON 工具参数，retry 没有兜底
milestones_total: 5
milestones_done: 1
---
## Goal
<project_goal expanded to one paragraph: what "done" looks like, what is out of scope>
## Log
| date | what happened | artifacts |
|------|---------------|-----------|
| 2026-06-23 | 建轨；拆 5 个里程碑；M1 跑通最小 REPL | milestones.md, cards 0001-0002 |
```
**`milestones.md`:**
```markdown
# Milestones — Build an LLM coding agent
- [x] M1 — Minimal REPL that calls the model once and prints a reply
- [ ] M2 — Tool-calling loop (model emits tool call → execute → feed result back)   <- current
- [ ] M3 — File read/edit + bash tools wired in
- [ ] M4 — Multi-step task completion with a stop condition
- [ ] M5 — Error handling + a real end-to-end demo
```
**Card from a trap (the highest-value applied artifact)** — ordinary card file, just tagged:
```markdown
---
id: card-0007
tags: [build-llm-agent, M2, trap]
---
**Q:** Why do naive `try/except: retry` loops fail when an LLM returns malformed tool-call JSON, and what's the fix?
**A:** Retrying the *same* prompt re-rolls the same failure distribution. Fix: feed the parse error back to the model as a tool result ("your JSON was invalid: <err>, return corrected args") so it self-corrects, and cap retries. — symptom: intermittent JSONDecodeError; cause: blind retry; fix: error-as-feedback + bounded retries.
```

### Data & State (what gets written where)
- **Source of truth:** `TRACK.md` (now carrying `project_goal` / `current_milestone` /
  `current_blocker` / milestone counts) + `milestones.md`. `registry.json` stays a rebuildable cache —
  `registry.py` reads only frontmatter it already understands plus the new optional milestone
  counters (additive, ignorable).
- **Cards** → `cards/card-NNNN.md`, Obsidian-SR-compatible, tagged with the milestone id and `#trap`
  when applicable. Scheduling state in `review-state.json` (no schema change — applied cards scheduled
  identically).
- **Notes** → `notes/` (per-session distilled note of what was built + why), wikilinked into
  `plan.md`, same as `domain`.
- **Worklog** → `worklog.md`, append-only session scratch; NOT a source of truth for cards (it's the
  raw input the distill step reads). Pasted code/errors in it are UNTRUSTED data.
- **Written only on approval, as one batch** (cards + note + MOC + state + milestone advance) — a
  pre-approval abort leaves the track unchanged, identical to the `domain` failure-mode contract.

### Failure modes
- **Distill with an empty/sparse worklog** → the tutor distills from the live dialogue; if there's
  genuinely nothing durable, propose **zero** cards rather than manufacturing filler (refusal policy
  from the card-quality gate). Never write empty cards.
- **Project lives in another repo / the learner never shares code** → fine by design:
  learn-everything owns *learning state*, not project code. Distillation works from dialogue + worklog
  notes; cards reference concepts, not file paths in a repo we don't track.
- **Milestone never finishes / stuck for many sessions** → `current_blocker` persists in `TRACK.md`;
  the status board flags the track as stale (same N-day threshold as the spine). The tutor may propose
  splitting the milestone, but does not auto-advance.
- **`milestones.md` and `TRACK.md` counters drift** → `TRACK.md` is authoritative for
  `current_milestone`; the `milestones_done/total` counters are recomputed from `milestones.md`
  checkbox state on each write (cheap reconciliation), and the board recomputes on rebuild.
- **Pasted error logs / stack traces / code (DATA_BOUNDARY)** → treated as UNTRUSTED data in both
  worklog and distill; scan for injection patterns and flag `[PROMPT_INJECTION_DETECTED]` rather than
  obeying. Especially relevant here since applied learners paste tool output constantly.
- **Confidential project (work codebase)** → README/skill warns that pasted code is sent to the host
  model; `tracks/` gitignored; confirm before ingesting proprietary code, same gate as legal `domain`.
- **FSRS / registry inputs** → unchanged from spine; applied adds no new engine inputs, so no new
  engine failure modes.

### Reuse vs build (explicit)
- **Reuse unchanged (engine):** `scripts/fsrs.py` and `scripts/registry.py` — zero changes. Applied
  is a new *mode*, not a new engine.
- **Reuse unchanged (data model):** card format, `review-state.json` sidecar, `plan.md` MOC, `notes/`,
  human-in-the-loop approval, DATA_BOUNDARY scanning — all inherited from the `domain` loop verbatim.
  The "distill" step is the same approve-then-write contract with a different *source* (a work session
  instead of a document).
- **Reuse (pedagogy borrows, ideas only — license-gated, rewritten):** `methods/learner-model.md`'s
  Theory-of-Mind silent inference; the **mastery-gate-before-advance** idea for `worked-example.md`
  from DeepTutor; the L1/L2/L3 + atomicity + dedup + refusal **card-quality rubric** — the same gate
  `domain` uses.
- **Reuse (the bigger product seam, NOT in this mode's scope):** the
  [URL → md adapter](#url--md-ingestion-adapter-send-a-link-learn-it) and project-repo readers stay
  OUT of core; applied mode neither requires nor implements them.
- **Genuinely new:** (1) `methods/worked-example.md` — the applied pedagogy template. (2) The
  **applied distillation loop** branch in `SKILL.md` — turning a *work session* (worklog delta +
  dialogue) into the same 3-bucket card/note proposal (concepts / traps / built-notes), with traps as
  a first-class `#trap`-tagged card type. The conceptual novelty: **learning extracted from doing,
  scheduled by the same FSRS net.** (3) Three additive `TRACK.md` fields + two per-track markdown
  files; ignorable by other modes.

### Verification (concrete checks)
- **No-engine-change proof:** `scripts/fsrs.py` and `scripts/registry.py` and their existing tests
  pass untouched after applied mode lands (regression: applied cards schedule identically to domain).
- **registry rebuild with an applied track:** a fixture `tracks/build-llm-agent/TRACK.md` (with the
  new fields) + `milestones.md` rebuilds to a valid `registry.json` row with `mode: "applied"`,
  correct `cards_total`, and (if surfaced) `M1/5` progress; unknown frontmatter keys do not break the
  `domain`/`exam` parsers.
- **End-to-end applied acceptance (mirrors the domain integration test):** `create` an applied track →
  `tracks/<id>/` with valid `TRACK.md` (`mode: applied`, `project_goal` set), `milestones.md` (≥3
  items), `worklog.md`; registered. Simulate a work session + `distill` on a sample worklog
  containing one trap → tutor proposes ≥1 concept card and ≥1 `#trap` card → **approve 2** → assert 2
  `cards/*.md` (one tagged `trap`), a `notes/` entry, `plan.md` MOC links, 2 `review-state.json`
  entries, a `TRACK.md` Log row, `current_milestone`/`next_action` advanced, milestone checkbox
  flipped. Abort a distill before approval → assert the track is byte-for-byte unchanged. `status`
  lists the applied track with its `next_action` and `cards_total: 2`. Simulate `now = created + 1
  day` → cross-track `review` surfaces the 2 applied cards alongside any domain cards; grade them →
  `due` dates advance per FSRS.
- **Pedagogy (model-behavioral, manual/eval):** with `pedagogy: worked-example`, the work-session loop
  surfaces a concept *before* the learner needs it and asks them to attempt the build step before
  explaining; switching to `feynman` makes distillation ask the learner to explain a trap back.
- **DATA_BOUNDARY:** a worklog seeded with an injected instruction in a pasted error log → distill
  flags `[PROMPT_INJECTION_DETECTED]` and does not obey.

### Phase / status
**Deferred past MVP** (MVP = spine + `domain` + shared engine). A **post-MVP mode addition**,
scheduled alongside/after `exam` mode — both validations of the spine's mode-polymorphism contract
that `domain` proves first. Intentionally cheap: reuses the engine and data model wholesale,
contributing exactly **one new method file + one SKILL.md branch + a few additive `TRACK.md` fields +
two markdown files**, with no engine change and no new dependency. Recommended to land after
`methods/learner-model.md` and the card-quality gate exist (the borrowed pieces it leans on).

**Open questions:** distill trigger granularity (per work-session — proposed — vs per-milestone, to
avoid card-fatigue). Whether the board surfaces milestone progress (M2/5) or stays mode-agnostic
(leaning additive display-only). Mastery-gating strength (demonstrated per-concept recall before
advancing vs. shipping the artifact being sufficient — likely advisory, not blocking). Whether
`worklog.md` auto-captures the pairing dialogue or stays manual (lean manual first cut). Relationship
to a future project-repo reader (out of scope; the worklog seam is where it would attach).

---

## Interop & Export Adapters (Anki + Obsidian companion)

> Two optional, out-of-core adapters that let learn-everything's atomic markdown cards and FSRS state
> flow into the wider review ecosystem **without compromising the pip-free portable CORE or the
> single-source-of-truth invariants**. Both live under `adapters/` (sibling to `scripts/`), are never
> imported by `scripts/` or the `learn` skill's core path, and degrade gracefully when absent. The
> defining rule for *every* interop path here: **`scripts/fsrs.py` + `review-state.json` is the ONE
> authoritative FSRS writer.** Anki and the Obsidian SR plugin are review *front-ends / mirrors*,
> never schedulers we read back from. **This is the resolution of the spec's Open Item (c) "two-way
> sync of FSRS state" — explicitly rejected in favor of one authoritative writer + read-only
> mirrors, to eliminate scheduler drift.**

### Goal
1. **Anki export** — let a learner take learn-everything cards into Anki, either as an offline
   `.apkg` (genanki) for portability/backup, or via a live AnkiConnect MCP push for in-session
   syncing. Re-exporting the same track must be **idempotent**: identical cards update in place, never
   duplicate, because GUIDs are derived deterministically from our stable `card-NNNN` ids.
2. **Obsidian companion deepening** — go beyond today's "open `tracks/` as a vault" (spec Open Item
   (a), already done in MVP) by surfacing each track's **due-card count + `next_action`** *inside*
   Obsidian (Open Item (b)), and settle the FSRS-drift question (Open Item (c)) by formally
   designating learn-everything as the single scheduler and obsidian-spaced-repetition (st3v3nmw) as a
   render-only review surface aligned on card *syntax* (already done in `_build_card_md`).

### Logic flow (numbered, end-to-end)

**A. Anki offline export (`adapters/anki_export.py`, genanki)**
1. User invokes export intent through the `learn` skill (or runs the adapter CLI directly):
   `python3 adapters/anki_export.py <track-id> [--out PATH] [--mode apkg|connect]`.
2. Adapter calls **CORE** read helpers from `scripts/registry.py` — `list_card_ids(track)`,
   `read_card_question(track, id)`, and a new sibling `read_card_answer(track, id)` (the only CORE
   addition; symmetric to the existing question reader, still stdlib) — to load each card's Q/A/tags.
   It does NOT touch `review-state.json` (FSRS state is not exported; Anki keeps its own scheduler
   once cards live there — we never read Anki's schedule back).
3. For each card, compute a **stable GUID** = `genanki.guid_for(f"learn-everything::{track_id}::
   {card_id}")`. Same input id → same GUID across runs → idempotent re-sync.
4. Build one genanki `Model` (fixed `model_id`, a `Basic`-style Front/Back template) and one `Deck`
   per track named `learn-everything::<track-title>` (fixed `deck_id` derived by hashing the track id,
   so the deck is stable too).
5. **DATA_BOUNDARY pre-scan** on Q/A text before writing (cards may contain ingested untrusted
   content): strip/flag zero-width + direction-override chars, refuse to embed anything that smells
   like injected HTML/script. Cards are data → never executed.
6. Write `<out>/<track-id>.apkg` (default `adapters/out/`, gitignored). Print a summary: N cards
   exported, deck name, GUID-stability note.

**B. Anki live push (AnkiConnect MCP, online)**
1. Same steps 1–2, but `--mode connect` (or the host model chooses this when an AnkiConnect MCP is
   connected).
2. This path is **host-driven, not a script**: the `learn` skill tells the host model to call the
   AnkiConnect MCP's `addNotes` / `updateNoteFields` tools, passing each card with its deterministic
   dedupe key. We additionally store our `card-NNNN` id in a hidden `LE-ID` field so re-pushes update
   by query `LE-ID:<id>` instead of duplicating.
3. The MCP server itself is **third-party / out-of-core** — we depend only on the *protocol shape*,
   not on bundling any specific server. README documents `ankimcp/anki-mcp-server` (MIT) as the
   recommended one.

**C. Obsidian companion — due counts + next_action surface**
1. learn-everything already writes `registry.json` (rebuildable cache holding per-track `next_action`,
   `last_active`, `cards_total`, and — extended here — `due_today`). The companion does **read-only**
   consumption of that file.
2. **Tier 1 (zero-build, ships in this adapter):** `adapters/obsidian_dashboard.py` renders
   `registry.json` → a single `tracks/_dashboard.md` MOC note with a table (track | mode | due today |
   next_action | last_active | deadline flag) and `[[wikilinks]]` into each `tracks/<id>/TRACK.md`.
   Opening the vault in Obsidian/Claudian shows a live board as a normal note. Regenerated on each
   `status`/`review`/ingest write (the `learn` skill calls it as a post-step), or on demand.
3. **Tier 2 (deferred, documented seam only):** a thin Obsidian community plugin (TS) that reads
   `registry.json` and shows due counts in the sidebar / status bar. NOT built here; the JSON contract
   (`registry.json` schema) is the stable seam so it costs nothing to add later. Out of core (TS,
   pip-irrelevant, separate dist).
4. **FSRS single-writer enforcement:** the companion never schedules. obsidian-spaced-repetition is
   configured/recommended in *review-on-render* alignment — our `_build_card_md` already emits its
   `#flashcards/<track>` + `?` syntax, so cards render and can be flipped in-vault, but the
   **authoritative due dates come from `review-state.json` via `scripts/fsrs.py`**, surfaced through
   the dashboard. README instructs users NOT to let the plugin's own scheduler write back (or to use
   it purely as a flip-through viewer), eliminating drift.

### Components
- `adapters/anki_export.py` — genanki offline `.apkg` writer (NEW, optional, pip: `genanki`).
- `adapters/anki_connect.md` — host-instruction snippet the `learn` skill loads when AnkiConnect MCP
  is present (no Python; pure method/prompt for the online push path).
- `adapters/obsidian_dashboard.py` — `registry.json` → `tracks/_dashboard.md` renderer (NEW; **stdlib
  only**, so this one piece *could* sit in core, but kept in `adapters/` for cohesion).
- `adapters/requirements.txt` — `genanki` only; documents that adapters opt into their own deps.
- CORE addition (single, minimal): `read_card_answer(track_id, card_id, root)` in
  `scripts/registry.py`, mirroring the existing `read_card_question`. Plus extend `_track_record` to
  include `due_today` (it already computes `_cards_due_today`).

### Interfaces (CLI / file formats / method files)
```
# Offline Anki export (idempotent)
python3 adapters/anki_export.py <track-id> [--out adapters/out/] [--mode apkg]
# Obsidian dashboard refresh
python3 adapters/obsidian_dashboard.py [--all | <track-id ...>]
# Online push: no CLI — host model calls AnkiConnect MCP tools per adapters/anki_connect.md
```
- **GUID contract (Anki):** `guid = genanki.guid_for("learn-everything::" + track_id + "::" +
  card_id)`. Fixed `MODEL_ID`/per-track `DECK_ID` constants documented in-file. Hidden `LE-ID` field
  on each note carries `card-NNNN` for AnkiConnect dedupe queries.
- **`registry.json` extension (additive, back-compatible):** each track record gains `"due_today":
  <int>`. Existing consumers ignore the unknown-but-present field; the rebuild path already has the data.
- **`tracks/_dashboard.md`:** a generated MOC note (gitignored with the rest of `tracks/`); header
  comment marks it auto-generated / do-not-hand-edit.

### Data & State (what gets written where)
- `.apkg` files → `adapters/out/<track-id>.apkg` (gitignored). No state mutation; pure read of cards.
- `tracks/_dashboard.md` → derived view of `registry.json`; rebuildable, never source of truth.
- **Nothing in these adapters writes `review-state.json`.** The hard invariant: one FSRS writer
  (`scripts/fsrs.py` via the core review path). Anki and the SR plugin own *their own* copies of
  scheduling once cards land there; we treat that as a one-way mirror and never reconcile back.
- AnkiConnect online path mutates the user's Anki collection (creates/updates notes) — outside our
  repo entirely.

### Failure modes
- **`genanki` not installed** → `anki_export.py` exits with a clear "optional adapter; `pip install
  -r adapters/requirements.txt`" message; CORE and the `learn` review loop are unaffected.
- **AnkiConnect MCP not connected / Anki not running** → host model reports it and offers the offline
  `.apkg` path; no silent failure.
- **Re-export drift / duplicates** → prevented by deterministic GUID + `LE-ID`. A card whose text
  changed updates the existing note. If a card is *deleted* in learn-everything, the Anki note is NOT
  auto-deleted (documented limit — we never destructively touch the user's Anki collection).
- **Two schedulers writing** (the core risk this design exists to kill) → structurally impossible on
  our side because adapters are read-only w.r.t. `review-state.json`; README + `anki_connect.md` warn
  against enabling the obsidian-spaced-repetition scheduler write-back.
- **Untrusted card content** (ingested via domain/applied loop) → DATA_BOUNDARY pre-scan in
  `anki_export.py` and a reminder in `anki_connect.md`; flag, don't embed/execute.
- **`registry.json` stale when dashboard renders** → dashboard first calls `rebuild_registry()`
  (existing CORE helper) so the board can't show stale due counts.

### Reuse vs build (explicit)
- **REUSE (adopt, MIT):** `genanki` for `.apkg` generation — pure-Python, stable GUID support; do not
  hand-roll a `.apkg` writer.
- **REUSE (interoperate, protocol only):** `ankimcp/anki-mcp-server` (MIT) for the online push — we
  depend on AnkiConnect's tool shape, bundle nothing.
- **REUSE (syntax alignment, already done):** st3v3nmw `obsidian-spaced-repetition` card markdown
  syntax — `_build_card_md` already emits `#flashcards/<track>` + `?`, so no work; the new decision is
  to formally make it render-only.
- **BUILD (genuinely new, small):** the GUID-derivation + `LE-ID` idempotency wrapper around genanki;
  `obsidian_dashboard.py`; `read_card_answer` CORE helper; the `due_today` registry field;
  `anki_connect.md` host snippet. None of this is a card-generation or scheduling engine — those are
  deliberately NOT built.
- **NOT built:** any second FSRS scheduler, any TS Obsidian plugin (Tier-2 seam only), any read-back
  reconciliation from Anki/plugin state.

### Verification (concrete checks)
- **Idempotency (the headline test):** export track twice → assert both `.apkg` files contain notes
  with identical GUIDs (unzip `.apkg`, read the sqlite `notes.guid` column or use genanki's API);
  importing the second over the first in a scratch Anki profile yields N notes, not 2N. Change one
  card's answer, re-export → same GUID, updated Back field.
- **GUID determinism (unit):** `guid_for("learn-everything::t::card-0001")` is stable across runs and
  differs per card id / track id.
- **Round-trip content:** exported note Front/Back equal `read_card_question`/`read_card_answer`
  output; tags preserved.
- **DATA_BOUNDARY:** a card containing a zero-width/RLO char and an "ignore previous instructions"
  line → export flags it, does not embed raw control chars.
- **Single-writer guarantee (regression):** grep/assert that nothing under `adapters/` calls
  `save_review_state` or writes `review-state.json`; run a full core review cycle and confirm
  `review-state.json` is byte-changed only by the `scripts/`-path, never by an adapter run.
- **Dashboard:** render against a 3-track fixture → `tracks/_dashboard.md` lists all tracks with
  correct `due_today` (cross-checked against `_cards_due_today`) and `next_action`; wikilinks resolve.
- **Core untouched:** run the existing MVP integration/unit suite with `adapters/` present and with
  `genanki` *uninstalled* → all pass (proves zero coupling / pip-free core preserved).
- **Manual (online):** with an AnkiConnect MCP connected, push a track, re-push → Anki shows
  updated-in-place notes, no duplicates (LE-ID query path).

### Phase / status
- **Phase 2 (post-MVP), isolated — schedulable independently of `exam`/`applied`** since each adapter
  reads only the already-stable CORE surface.
- **Sub-order:** (1) `obsidian_dashboard.py` + `due_today` registry field + the single-FSRS-writer
  decision/README (stdlib, near-zero risk, immediate dogfood value in Claudian) → (2) `anki_export.py`
  genanki offline path + idempotency tests → (3) `anki_connect.md` online push (gated on a connected
  AnkiConnect MCP) → (4) Tier-2 TS Obsidian plugin only if the dashboard-as-note surface proves
  insufficient.
- **Invariants honored:** CORE stays pip-free (adapters carry their own `requirements.txt`, never
  imported by core); markdown cards stay the source of truth; one authoritative FSRS writer, adapters
  strictly read-only on schedule state; reuse genanki + AnkiConnect + st3v3nmw rather than rebuild.

**Open questions:** Anki note deletion policy (prune orphaned notes via a manifest of
previously-exported GUIDs vs. strictly non-destructive — current proposal). Whether offline export
should ALSO seed Anki's scheduler from `review-state.json` on first export (convenient migration, but
muddies the one-writer line — current design exports content only). Whether to build the Tier-2
Obsidian plugin or rely on the dashboard note (decide after dogfooding in Claudian). Whether
obsidian-spaced-repetition can be reliably configured render/flip-only per-vault. Stable
DECK_ID/MODEL_ID collision risk across many tracks/users sharing one Anki profile (per-install salt
vs. fixed product constant).

---

## Publish & Packaging

> Make the skill-first repo installable and trustworthy as an open-source product **without touching
> the portable core**. At publish time, add a thin `.claude-plugin/` manifest + marketplace entry
> *around the same files* (no change to `scripts/`, `methods/`, `skills/learn/SKILL.md`), give two
> honest install stories (Claude Code terminal users; Obsidian/Claudian users), ship a data-free
> `examples/` track so a fresh clone has something to look at, add `CHANGELOG.md` + SemVer tags, and
> wire CI running the existing `unittest` suite plus the py-fsrs parity oracle from
> [Engine Hardening](#engine-hardening-fsrs-parity--personalized-weights--configurable-retention).
> The MVP/later line is drawn explicitly.

### Logic flow (numbered, end-to-end)
1. **Pre-publish gate (manual, once):** confirm invariants — core is pip-free (`grep -rn "import "
   scripts/` shows stdlib only), `.gitignore` excludes `tracks/*`, `profile.md`, `registry.json`; no
   private data in tracked files (spot-check for the author's real track ids like
   `share-swap-restructuring`, `换股重组`, client names).
2. **Add packaging files** (the only additions): `.claude-plugin/plugin.json`,
   `.claude-plugin/marketplace.json`, `CHANGELOG.md`, `examples/`, `.github/workflows/ci.yml`,
   `tests/test_fsrs_parity.py`, `requirements-dev.txt` (py-fsrs pin, dev-only). The skill, scripts,
   methods, README files are untouched. (Note: `tests/test_fsrs_parity.py` + `requirements-dev.txt`
   are shared with Engine Hardening item (1) — the same artifacts serve both features.)
3. **CI runs on every push/PR:** matrix Python 3.10–3.13 → (a) `python -m unittest discover -s tests`
   (the existing tests, zero deps) on all versions; (b) on one version only, `pip install -r
   requirements-dev.txt` then `python -m unittest tests.test_fsrs_parity`. CI green is the merge gate.
4. **Cut a release:** bump version in `plugin.json` + add a `CHANGELOG.md` entry under a new `## [x.y.z]
   - DATE` heading, commit `chore(release): vx.y.z`, tag `vx.y.z` (annotated), push tag. (Optional
   later: a GitHub Release with auto-generated notes.)
5. **Marketplace listing:** `marketplace.json` points at this repo; users add the marketplace and
   install the `learn` plugin (Claude Code path), OR clone the repo into/alongside their Obsidian vault
   (Claudian path).
6. **Fresh-clone smoke (part of release checklist):** clone clean, run the clean-clone product test
   already in the spec §Verification against the shipped `examples/` track, confirm no private data
   and that `learn` creates a track end-to-end.

### Components
- **`.claude-plugin/plugin.json`** — the thin manifest that turns the existing `skills/learn/` into an
  installable Claude Code plugin. References the *same* `skills/learn/SKILL.md`; no `commands/`,
  `hooks/`, or `agents/` (the spec's skill-first decision stands — one skill, NL-triggered, optional
  `/learn` alias only if Claude Code auto-derives it from the skill).
- **`.claude-plugin/marketplace.json`** — single-plugin marketplace entry so `learn-everything` is
  installable via `/plugin marketplace add <repo>` then `/plugin install learn-everything`.
- **`CHANGELOG.md`** — Keep-a-Changelog format, SemVer. Seeded with `## [0.1.0]` documenting the
  shipped MVP (spine + domain mode + FSRS-6 engine + method files + learn skill).
- **`examples/`** — one data-free demo track (see Interfaces) so a clean clone is explorable without
  private `tracks/` data. Committed (NOT gitignored — the public counterexample to `tracks/`).
- **`.github/workflows/ci.yml`** — GitHub Actions: unittest matrix + py-fsrs parity job.
- **`tests/test_fsrs_parity.py`** — dev/CI-only oracle test (closes the "NUMERIC PARITY DEFERRED"
  caveat; same artifact as Engine Hardening item (1)).
- **`requirements-dev.txt`** — pins `py-fsrs==<x>` for CI/dev only. A one-line comment states it is
  NEVER a runtime dependency; the product still runs on stdlib alone.

### Interfaces (CLI subcommands / file formats / method files)
No new CLI subcommands and no method-file changes — packaging adds metadata + CI only. New file
formats:

**`.claude-plugin/plugin.json`**
```json
{
  "name": "learn-everything",
  "version": "0.1.0",
  "description": "Multi-track learning OS: a thin orchestrator over a stdlib-Python FSRS engine. Tracks, spaced-repetition cards, and Socratic/Feynman/active-recall tutoring — markdown is the source of truth.",
  "author": { "name": "<author>" },
  "homepage": "https://github.com/<owner>/learn-everything",
  "license": "MIT",
  "keywords": ["learning", "spaced-repetition", "fsrs", "tutor", "flashcards", "obsidian"]
}
```
(`version` is the single source of truth for the release number; `CHANGELOG.md` mirrors it. Skills are
auto-discovered from `skills/` — the manifest does not re-list `SKILL.md`.)

**`.claude-plugin/marketplace.json`**
```json
{
  "name": "learn-everything",
  "owner": { "name": "<author>" },
  "plugins": [
    { "name": "learn-everything", "source": "./", "description": "Multi-track learning OS (FSRS + tutor pedagogy, markdown-native)." }
  ]
}
```

**`examples/` layout** — a real, committed track folder mirroring `tracks/<id>/` exactly, with neutral
public content (e.g. a "photosynthesis" or "TCP handshake" domain track):
```
examples/
  README.md                       # "copy this into tracks/ to try, or just read it"
  demo-track/
    TRACK.md                      # mode: domain, pedagogy: socratic, status: active
    plan.md                       # MOC with [[wikilinks]]
    cards/card-0001.md … 0003.md  # Obsidian SR syntax (#flashcards/demo + ? separator)
    notes/2026-06-22-intro.md
    review-state.json             # 3 seeded FSRS entries
```
The `examples/` README explains the layout maps 1:1 to a real `tracks/<id>/`, so the demo doubles as
living documentation of the data model.

### Data & State (what gets written where)
- **Repo-tracked additions only**: `.claude-plugin/*`, `CHANGELOG.md`, `examples/**`,
  `.github/workflows/ci.yml`, `tests/test_fsrs_parity.py`, `requirements-dev.txt`. None touch user
  state.
- **No runtime state change**: user state still lives where the spec says — `tracks/<id>/TRACK.md`
  (truth), `review-state.json` (FSRS sidecar), `registry.json` (rebuildable cache, gitignored).
  Packaging writes nothing at runtime.
- **`examples/` is the only committed track-shaped data** and is deliberately public/neutral — the
  inverse of gitignored `tracks/*`. `.gitignore` needs **no change** (it ignores `/tracks/*` and
  `/registry.json`, not `/examples/`); confirm `examples/` is not caught by any future glob.
- **Version is stored once** in `plugin.json`; CHANGELOG and the git tag mirror it.

### Failure modes
- **Private data leaks into the public repo** → pre-publish gate greps tracked files for known private
  track ids / Chinese client terms; `examples/` exists precisely so contributors never reach for real
  `tracks/` data. If `tracks/` was ever force-added, `git ls-files tracks/` must return only
  `tracks/.gitkeep`.
- **CI flakes because py-fsrs changed defaults** → parity test pins an exact py-fsrs version; a bump
  is a deliberate PR that also re-checks `DEFAULT_WEIGHTS`. Parity runs on one Python version only, so
  it can't block the dep-free matrix.
- **Someone assumes py-fsrs is a runtime dep** → it lives in `requirements-dev.txt` (not
  `requirements.txt`, which does not exist), with an explicit "DEV/CI ONLY" comment; README install
  steps never pip-install anything for the core path.
- **Claudian can't run the Python scripts in-vault** (open item) → install docs state the Obsidian
  one-app story as *recommended-pending-spike*, with the external-terminal Claude Code path as the
  always-works fallback. Do not claim the in-vault path works until the spike passes.
- **Marketplace/plugin schema mismatch** → keep `plugin.json` minimal; validate by actually running
  `/plugin marketplace add ./` + `/plugin install` once before tagging, rather than trusting the JSON
  blind.
- **Version drift** (tag ≠ plugin.json ≠ CHANGELOG) → release checklist makes bumping all three a
  single step; a CI guard (later) can assert `plugin.json` version == latest CHANGELOG heading.

### Reuse vs build (explicit)
- **Reuse, no rebuild:** `skills/learn/SKILL.md`, `scripts/fsrs.py`, `scripts/registry.py`,
  `methods/*.md`, `README.md`, `README.zh.md`, `LICENSE`, `profile.example.md` — all ship unchanged.
  Packaging is a *wrapper*, honoring the spec's "publish-time wrapper (deferred, cheap)" decision.
- **Reuse (external, dev-only):** open-spaced-repetition/py-fsrs (MIT) as the CI parity **oracle**.
  Pinned, dev-only, never runtime. Use the fsrs4anki wiki when authoring fixtures (same-day reviews,
  lapses); fsrs-rs as the tie-breaker authority if py-fsrs and the ecosystem disagree.
- **Reuse (install-story only):** Claudian (MIT) as the documented Obsidian host and
  st3v3nmw/obsidian-spaced-repetition (MIT) for native in-vault card review — the `examples/` cards
  already use its `#flashcards/<track>` + `?` syntax. No code vendored; these are README instructions.
- **Genuinely new (this feature):** the `.claude-plugin/` manifest + marketplace entry, `CHANGELOG.md`,
  the `examples/demo-track/` data-free track, `.github/workflows/ci.yml`, `tests/test_fsrs_parity.py`,
  `requirements-dev.txt`, and the two-path install section in the READMEs. All additive; zero core change.

### Verification (concrete checks)
- **Manifest loads:** `/plugin marketplace add ./` then `/plugin install learn-everything` in a Claude
  Code session succeeds and the `learn` skill triggers on "what am I learning". (Manual,
  release-checklist step.)
- **CI green:** `python -m unittest discover -s tests` passes on Python 3.10–3.13 with **no pip
  install** (proves the pip-free invariant in CI itself); the parity job passes on one version after
  `pip install -r requirements-dev.txt`.
- **Parity test:** `tests/test_fsrs_parity.py` asserts `scripts/fsrs.py schedule` output matches
  py-fsrs across a grid of `(rating ∈ {1,2,3,4}, elapsed_days, state)` within tolerance; out-of-range
  grade still rejected (re-uses existing validation).
- **Clean-clone product test:** fresh `git clone`, empty `tracks/`, run the spec §Verification
  "Product (clean-clone)" steps against `examples/demo-track/` (copied into `tracks/`); assert a new
  `learn "Test"` track is created end-to-end and `.gitignore` excludes `tracks/` + `profile.md`.
- **No-private-data check:** `git ls-files tracks/` == `tracks/.gitkeep` only; grep tracked files for
  known private ids returns nothing; `examples/` contains only neutral public content.
- **Version coherence:** `plugin.json` `version` == top `CHANGELOG.md` entry == pushed git tag.

### Release checklist (concrete)
1. Pre-publish gate: pip-free grep on `scripts/`, `.gitignore` correct, no private data (`git ls-files
   tracks/`).
2. Run full suite locally: `python -m unittest discover -s tests` → green.
3. Run parity locally: `pip install -r requirements-dev.txt && python -m unittest
   tests.test_fsrs_parity` → green.
4. Bump `version` in `.claude-plugin/plugin.json`.
5. Add `## [x.y.z] - YYYY-MM-DD` section to `CHANGELOG.md` (Added/Changed/Fixed).
6. Verify install path: `/plugin marketplace add ./` + `/plugin install learn-everything`; trigger the
   skill once.
7. Verify clean-clone story against `examples/` per §Verification.
8. Commit `chore(release): vx.y.z`; tag annotated `vx.y.z`; push commit + tag.
9. (Optional) Create a GitHub Release from the tag with the CHANGELOG section as notes.

### Phase / status
- **At publish time (this feature), MVP-adjacent:** `.claude-plugin/plugin.json`, `marketplace.json`,
  `CHANGELOG.md` `[0.1.0]`, `examples/demo-track/`, README two-path install section,
  `.github/workflows/ci.yml`, `tests/test_fsrs_parity.py` + `requirements-dev.txt`. Small, additive,
  no core change — safe to do whenever the author decides to publish.
- **Later (post-dogfooding):** GitHub Release automation; a CI guard asserting version coherence;
  resolving the Claudian-runs-Python spike before upgrading the Obsidian path from
  "recommended-pending-spike" to "supported"; the Anki-export and URL-ingest adapters ship as their
  own opt-in packages with their own (pip-bearing) deps, documented as adapters — they get their own
  CHANGELOG entries when added.
- **Explicitly NOT in this feature:** `commands/`, `hooks/`, `agents/`, a dashboard, or the MCP server
  wrapper — those remain deferred per the spec's skill-first decision; the MCP seam is still phase 2.

**Open questions:** Claude Code plugin manifest schema specifics (exact field names, skill
auto-discovery vs explicit listing, whether `marketplace.json` `source: "./"` is valid for a
single-repo marketplace) should be validated against the current Claude Code plugin docs before
tagging. Whether `/learn` becomes an actual slash command depends on whether Claude Code auto-derives
a command from a skill named `learn` (the spec wants no `commands/`). Exact py-fsrs version to pin +
acceptable numeric tolerance (one dev pass). The Claudian-runs-Python-in-vault spike gates whether the
Obsidian install story is "supported" or "provisional". Whether to publish to a public marketplace now
or after dogfooding (a product decision, not resolved here).
