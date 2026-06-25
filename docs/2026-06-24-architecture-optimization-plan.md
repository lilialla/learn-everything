# learn skill — architecture optimization plan (to MATURE & USABLE)

> **SUPERSEDED (2026-06-25) — historical snapshot.** This plan recommended *freezing* the deferred
> backlog (exam/applied modes, URL/long-document ingestion, MCP, FSRS weights). That decision was
> later reversed: those features are now **built as optional out-of-core adapters/modes** (see the
> CHANGELOG `[Unreleased]`). Read the P0/P1 *maturity* items below as the rationale that shaped the
> current `skills/learn` design; ignore the "freeze the backlog" recommendation — it no longer holds.

Date: 2026-06-24
Synthesizer input: 5-dimension audit (invocation/feedback, memory, teaching quality, UX/小白化, adversarial maturity).
Scope: take `skills/learn` from "MVP shipped + audited" to "mature & usable" with the SMALLEST change set.

Invariants respected throughout: pip-free stdlib CORE; markdown = source of truth, `registry.json` = rebuildable cache;
cards Obsidian-spaced-repetition compatible; single SKILL.md adapter; teach-first; human-in-the-loop approval before
persist; DATA_BOUNDARY; reuse-not-rebuild; confidentiality (tracks/, registry.json, profile.md gitignored).

---

## 1. Maturity assessment (honest)

**Where it is now.** The deterministic spine is genuinely good and over-built relative to delivered value:
`registry.py` (1,334 lines) + `fsrs.py` (212 lines) give a correct FSRS scheduler, a deterministic plan-day ranker,
a status board with real nudges (`needs_cards`, `mission_present`), atomic writes that survive Drive sync, and one
hard pre-flight gate (`ingest-check`). The pedagogy `methods/*.md` are deep and operationalized, not summaries.

**But the core promise has not yet been delivered even once.** Ground truth from the live vault confirms the
adversarial read:

- Both real tracks have **0 cards** (`cards/` empty in both). FSRS — the entire point — has caught nothing.
- `tracks/rag-techniques/TRACK.md`: `next_action: null` AND an **empty Log table**, despite a full ingest session
  (`notes/2026-06-24-map.md` + saved original exist). RESUME there returns a blank pointer + zero learning memory.
- `tracks/datawhale-llm/ingest-session-20260624-rag-article.md` (8.5 KB) is the **"card factory" leftover** — an
  unapproved proposal dumped at track root, invisible to every CLI command. The product ships evidence of its own
  anti-pattern.
- `plan.md` is the empty skeleton in both tracks. `learning-records/` is spec'd but never written, absent everywhere.
- `profile.md` does not exist (only `profile.example.md` does — see correction below), so plain-language /
  response-language personalization never activates.

**What "mature & usable" means here (the bar):** one non-technical user can, inside Obsidian/Claudian, (a) go from
zero to a first taught concept + ≥1 card in minutes, (b) leave every session with a resume pointer and a retention
trace, (c) return days later and have the system reconstruct "what you learned / where you are / what's due", and
(d) see that retention is working. Concretely the adversarial bar: **one user, one track, ≥10 cards, ≥3 review days.**

**The gap is not more engine.** It is: close the loop (sessions must leave a card-or-reason + a resume pointer),
reconstruct learning context on return (a CONTEXT digest), make first value fast, speak human (strip jargon, first-run
onboarding), and re-engage (lead every surface with the due count). Almost all of it is SKILL.md wording + 3 tiny
read-only CLI additions. The deferred ~3,000-line backlog (exam/applied modes, URL/long-doc ingestion, personalized
FSRS weights) is over-build against an empty deck and must be frozen.

**Correction to the audit input:** Dimension 4 claims "profile.md ... has no template and is never created." Half
wrong: `profile.example.md` **does exist** at repo root. The real gap is (a) it is never copied to `profile.md` / wired
into a first-run hook, and (b) the example itself leaks jargon (it lists `socratic`/`feynman`/`active-recall` as the
user-facing options). Proposals below reflect this.

---

## 2. P0 — required for mature & usable (implement now, in this order)

P0 is deliberately small: **3 CLI additions + one focused SKILL.md rewrite pass + 2 doc/hygiene fixes.** Sequenced so
all `scripts/registry.py` edits land first (one test pass), then all `skills/learn/SKILL.md` edits as a single coherent
rewrite, then docs/cleanup.

### Group A — `scripts/registry.py` (do all three together, one `tests/test_registry.py` pass)

These are the only engine changes in P0. All are read-mostly, stdlib, additive, registry stays rebuildable.

**A1. `session-check` subcommand — enforce "a session leaves a retention trace"**
- kind: code · file_target: `scripts/registry.py` (+ `tests/test_registry.py`)
- what: New subcommand `python3 scripts/registry.py session-check --track <id>` returning
  `{ok: bool, reason: str}`. `ok:false` when the most recent `## Log` row added `cards_delta == 0` AND that row carries
  no `no-cards-reason:<text>` marker. This makes teach-first measurable: a teaching session may skip cards, but never
  silently — it must add ≥1 card OR log an explicit reason. Reuse existing TRACK.md Log parsing. Pair with a `--no-cards-reason`
  passthrough on the existing `log` subcommand so the skill can record the allowed second state. ~40 lines + tests.

**A2. `status` leads with the due count + adds `resume_pointer_missing`**
- kind: code · file_target: `scripts/registry.py` (`status_board()` already computes the inputs)
- what: (i) Add a top-level field to the `status` payload: `due_total` and `tracks_with_due` (sum over
  `cards_due_today`) so EVERY status surface can lead with "N cards due across M tracks" — the single re-engagement
  pull. (ii) Add a per-track read-only signal `resume_pointer_missing: true` when a track has session/notes evidence
  (`taught_since_created` is already computed) but `next_action` is null AND zero Log rows — exactly the
  rag-techniques failure. This is the same shape as the existing `needs_cards` nudge; no new state. ~20 lines + tests.

**A3. `progress` view (or fold into `status`) — show retention is working**
- kind: code · file_target: `scripts/registry.py` (small `progress` subcommand)
- what: Per-track 3 numbers, pure read over `review-log.jsonl` + `review-state.json`: cards_total /
  cards_graduated (FSRS interval > 21d) / 7-day review accuracy. The motivational payoff that makes SR habit-forming
  and proves the system does something. Resist a dashboard — exactly 3 numbers. ~35 lines + tests.

> Why these three and not the deferred `flow-check`/`track_kind`: `flow-check` (D1 P2) and `track_kind` (D2 P2) are
> correctly deferred — prose gating + default=domain already cover their cases; adding CLI surface now is speculative
> against an empty deck. `session-check`, the due-count lead, and `progress` each directly unblock the maturity bar
> (loop closes, re-engagement exists, retention is visible) and are read-mostly.

### Group B — `skills/learn/SKILL.md` (single coherent rewrite pass — same file, do as one edit set)

All of the following touch one file; implement together so the ground rules and per-intent text stay consistent.

**B1. Ground rule: NEVER expose internal vocabulary; speak like a tutor**
- kind: skill · what: Add a ground rule that the intent labels (STATUS/RESUME/INGEST/CREATE/PLAN-DAY), and the words
  FSRS / pedagogy / MOC / "mission stub" / registry / `ingest-check` / `mode` are IMPLEMENTATION terms the user must
  never see. Talk human: "learn this / pick up where we left off / what should I do today / how am I doing." Scrub the
  example lines throughout SKILL.md to remove leaked jargon. (Dedupes D4 "strip vocabulary" + D4 "translate blockers".)

**B2. Ground rule: TRANSLATE engine blockers/errors into plain terms**
- kind: skill · what: Companion to B1. When `ingest-check` returns blockers or any CLI errors, never echo the raw
  string. Mapping: mission stub → "First let's pin down WHY you're learning this — one minute, it makes everything
  sharper."; unknown track → "I don't see that one yet — want me to start it?"; status!=active → "That one's paused —
  resume it?". The deterministic gate stays underneath; only surfacing changes.

**B3. Mandatory one-line session-state header every turn (orientation)**
- kind: skill · what: New ground rule: the first line of every assistant turn inside any sub-flow prints a compact
  state line, e.g. `[learn · teaching · concept 2/4 (向量检索) · next: probe]`, `[learn · review · card 3/8 · next:
  grade]`, `[learn · today's plan · block 2/5 · ~18 min left]`. Specify the counters each intent must carry. Note: per
  B1 the bracket uses human words ("teaching"/"review"/"today's plan"), not INGEST/REVIEW. Fixes "you are here" +
  "what's next / how much left" with zero engine change, and passively forces the model to know which step it is in.
  (Dedupes D1's session-state line with D4's no-jargon rule.)

**B4. First-run / empty-vault onboarding + QUICKSTART (the first-win path)**
- kind: skill · what: Branch STATUS on an empty board: do NOT show a blank table — greet warmly, give 2–3 concrete
  examples in the user's language, and offer the one move: "tell me what you want to learn." On their first answer,
  run CREATE **silently with defaults** (derive the slug, mode=domain, pedagogy=tutor — never ask, never show the id).
  Add a compressed first-win loop: create with a 1-line goal (defer full MISSION, leave the stub + later nudge), teach
  ONE concept dialogically, land 1–2 cards — so first value is ~5–10 min, not the full 35–40 min ceremony. The deep
  diagnose/MISSION/learning-science path remains the default for subsequent sessions, not the gate to first value.
  (Merges D4 "first-run branch" + D4 "silent defaults" + D5 "QUICKSTART 5-min win".)

**B5. Reframe pedagogy as plain "teach me / quiz me / explain back"; never print method names**
- kind: skill · what: Wherever the skill offers a method, present outcomes not names: "I can walk you through it, quiz
  you, or have you explain it back to me (that exposes gaps fastest)" → map internally to tutor / active-recall /
  feynman. Remove "confirm the id with the user" and the jargon menu. (Dedupes D3's selection table user-facing layer
  with D4's "teach me/quiz me".)

**B6. Pedagogy-SELECTION rule (material × learner × goal → method)**
- kind: skill · what: Short decision rule (internal, ~15 lines) used at FRAME and at REVIEW: knowledge/theory text →
  tutor (the safe default ONLY for knowledge tracks, not for everything); procedural/math/coding/worked-solution
  material → worked-examples (new method, see B-method P1); a skill to perform → deliberate-practice; learner state
  from learner-model (fragile→re-teach, solid/bored/over-confident→elaboration, leech→socratic/feynman). This is the
  decisive content fix and is selection logic, not engine state. (Keeps the *rule* in P0; the two new method files it
  references are P1 — until they exist, the rule degrades gracefully to tutor/active-recall.)

**B7. Hard "leave a resume pointer + retention trace" contract on session close**
- kind: skill · what: Make the final `log` mandatory and non-skippable at the end of every INGEST and RESUME teaching
  session: never end with `next_action=null` AND empty Log (the rag-techniques failure). If there's no clean next
  step, log the most recent concept + "continue from here." Then run `session-check` (A1) before declaring done; if it
  returns `ok:false`, either add a card or record `no-cards-reason`. (Merges D2 "always leave a pointer" + D5 "session
  leaves a retention trace.")

**B8. CONTEXT.md — the per-track digest RESUME reads FIRST**
- kind: skill · what: Define `tracks/<id>/CONTEXT.md` (markdown, Obsidian-friendly) with fixed sections: "Where you
  are", "What you've learned", "Known sticking points", "Open threads". RESUME reads CONTEXT.md first, then falls back
  to frontmatter/Log. Session-close (B7) writes/updates it. STATUS, for the top track, shows a 2–3 line recap from it
  ("Last time: taught X; you were shaky on Y; next: Z"). It is markdown-is-truth, NOT engine state — registry stays
  rebuildable, no CLI schema change. This is the smallest fix for memory reconstruction (D2 2a+2b). Point
  `methods/learner-model.md` persistence at CONTEXT.md's "Known sticking points". (Merges D2 CONTEXT digest + D2 STATUS
  recap; also subsumes D2's separate learning-records firing into "write the rolling digest now; dated
  learning-records/ is a P1 detail layer.")

**B9. Artifact hygiene: proposals only under `notes/`, scan for orphans on RESUME**
- kind: skill · what: One line: ingest card proposals live ONLY at `tracks/<id>/notes/<date>-card-proposal.md`
  (already SKILL.md Step 5) — never at track root. On RESUME, glob the track dir for unlinked `.md` not referenced in
  plan.md/Log and offer to finish-persist / move to notes/ / discard. (Merges D2 orphan reconcile + D5 hygiene rule.)

**B10. Compress INGEST to load-bearing beats; push detail to methods/**
- kind: skill · what: SKILL.md is 258 lines and over-relies on the model obeying many prose steps. Keep the three
  beats the model cannot fudge — (1) `ingest-check` gate, (2) the FORBIDDEN "teach before any card" block, (3)
  `session-check` close (A1) — and move the diagnose/learning-science prose into `methods/learner-model.md` /
  `methods/learning-science.md`, referencing them. Smaller skill = more reliably followed. (D5 "trim 8 gates to 3.")

### Group C — docs & hygiene (independent, do last)

**C1. Remove the card-factory leftover + (do NOT re-create as orphan)**
- kind: doc · file_target: `tracks/datawhale-llm/ingest-session-20260624-rag-article.md` (delete)
- what: Delete the orphaned 8.5 KB unapproved proposal at track root. (B9 prevents recurrence.) 5 min. NOTE: tracks/
  is gitignored, so this is a local-vault cleanup, not a repo change.

**C2. profile.md activation + de-jargon the example**
- kind: doc · file_target: `profile.example.md` (edit) + `skills/learn/SKILL.md` (first-run hook — folds into B4)
- what: Correction-aware: the template exists. (i) Rewrite the "Preferred pedagogy" section of `profile.example.md`
  to use plain language ("teach me / quiz me / I explain it back") instead of socratic/feynman/active-recall. (ii) On
  the very first session only, offer to set 2–3 prefs (response language, plain vs technical, teach vs quiz) in one
  breezy question, then write `profile.md`. Optional/skippable.

**C3. README re-lead with the in-Obsidian path + Day-1 checklist + re-engagement recipe**
- kind: doc · file_target: `README.md`
- what: Reorder Quick start so the headline is: open the folder as an Obsidian vault → add Claudian → type "I want to
  learn X". Move raw `python3 scripts/registry.py …` into a collapsed "Advanced / direct CLI" note. Add a single
  linear "Day 1" checklist for a non-technical user including the Claudian macOS 401 fix (SDK reads
  `~/.claude/.credentials.json`). Add the re-engagement recipe: one copy-paste line the user can drop in a Daily Note /
  cron / scheduled task to run `registry.py status` and see the due count — NOT a notification daemon. (Merges D4
  README re-lead + D5 first-run checklist + D5 re-engagement surface.)

**C4. Freeze the deferred backlog (anti-over-build gate note)**
- kind: doc · file_target: `plans/specs/2026-06-22-feature-designs.md` (one note at top)
- what: "BLOCKED until the core retention loop is demonstrably sticky for one user on one track (≥10 cards, ≥3 review
  days)." Explicitly defers exam mode, applied mode, URL/long-document ingestion, and personalized FSRS weights.

**Sequencing rationale:** Group A (engine) first → one `tests/test_registry.py` run validates `session-check`,
`due_total`/`resume_pointer_missing`, `progress`. Group B (SKILL.md) second as ONE rewrite so B1–B10 stay internally
consistent and reference the now-existing CLI. Group C last (independent docs + a vault file deletion).

---

## 3. P1 — strong follow-up (after P0 lands and is exercised once)

- **P1-1. `methods/worked-examples.md`** (kind: method) — Cognitive Load Theory + fading (I-do→we-do→you-do,
  completion problems, expertise-reversal caveat, self-explanation prompts, harvest stumbles as L2/L3 cards). The
  single biggest pedagogy hole; procedural/STEM/coding tracks have no correct scaffold today. B6's selection rule
  already references it. ~120-line data file.
- **P1-2. `methods/deliberate-practice.md`** (kind: method) — Ericsson targeted skill drills (isolate sub-skill at the
  edge → measurable target → short reps → immediate corrective feedback). Distinct from REVIEW (FSRS recall) and from
  teaching. Hook a "drill" plan-day block kind later if real use needs it.
- **P1-3. Wire dated `learning-records/`** (kind: skill) — activate the spec'd-but-dead store as the detail layer
  behind CONTEXT.md (CONTEXT = rolling summary; learning-records/NNNN-slug.md = dated decision-grade insight). Add the
  firing step + one example in SKILL.md; clarify the CONTEXT vs learning-records relationship in
  `methods/learning-science.md`.
- **P1-4. `methods/metacognition.md`** (kind: method) — thin cross-cutting layer: predict-then-compare calibration,
  plan→monitor→evaluate, catch re-reading masquerading as learning. Ties to the FSRS self-grade ("grade by feel").
- **P1-5. `methods/dual-coding.md` + interleaving hook** (kind: method) — promote two named-but-not-runnable principles
  to moves: pair verbal with a complementary visual (ASCII/mermaid/table), concrete↔abstract pairing, brief CPA note;
  add a 2-line interleaving note so REVIEW/plan-day mix sub-topics rather than block by topic.
- **P1-6. De-duplicate card-derivation (L1/L2/L3 + quality gate)** (kind: method) — make `methods/active-recall.md` the
  single source; have socratic/feynman/elaboration reference it by one line. Pure maintenance, no behavior change.

---

## 4. P2 — later (nice, not gating)

- **P2-1. `flow-check` / `resume-check` CLI backstop** (code) — only if real sessions show RESUME/REVIEW free-wheeling
  despite the P0 prose checklists. Smallest viable form = parametrize `ingest_check`, not a second function.
- **P2-2. `track_kind` frontmatter (exam|domain|project)** (code) — shape plan-day scoring per progress type. Keep
  default=domain so existing tracks behave identically. Defer until ≥2 tracks of different kinds exist.
- **P2-3. `methods/productive-failure.md`** (method) — generate-before-instruction for well-structured problems;
  composes with worked-examples (failure first, then the worked example).
- **P2-4. Mark personalized FSRS weights as deferred** (doc) — stock FSRS-6 defaults are excellent; personalization
  needs hundreds of reviews. Revisit only after a real track has >200 graded reviews. (Folds into C4's freeze.)

---

## 5. CUT or SIMPLIFY (maturity is also subtraction)

- **CUT now: the ~3,000-line deferred feature backlog** (exam mode, applied mode, URL ingestion, long-document
  ingestion, personalized FSRS weights). Building breadth against a 0-card deck is the central maturity risk. Gate it
  behind the stickiness bar (C4).
- **CUT: personalized/optimized FSRS-6 weights.** Pure gold-plating with no review history. Keep stock defaults.
- **SIMPLIFY: SKILL.md from 8 prose gates to 3 enforced beats** (B10). The model already shortcut the prose once; a
  shorter skill with deterministic backstops is followed more reliably than a longer one with more exhortation.
- **DROP from P0 (defer, don't build): `flow-check` and `track_kind`** — prose gating + default=domain cover their
  cases; adding CLI surface now is speculative.
- **DON'T add a notification daemon** for re-engagement — the due-count lead line (A2) + a documented copy-paste
  recipe (C3) achieve the same with zero infra and no invariant risk.
- **SIMPLIFY memory: ONE digest file (CONTEXT.md), not a new engine state store.** Resist making the digest an engine
  schema; keeping it markdown preserves the rebuildable-cache invariant and avoids a migration.

### Invariant-risk flags

- **B8 CONTEXT.md / B7 mid-session writes:** more frequent writes under Drive sync — SAFE because writes are atomic
  (D11). Do NOT promote CONTEXT.md into `registry.json`/engine state (would break rebuildable-cache).
- **A2/A3:** read-only over existing artifacts; no new persisted state — invariant-safe.
- **A1 session-check:** parses TRACK.md Log (already source of truth) — no new state, invariant-safe.
- **B4 silent CREATE defaults:** must still leave the MISSION stub + STATUS nudge so grounding isn't permanently
  skipped — preserves the learning-science grounding intent while removing the 小白 friction.
- **None of P0 touches the FSRS algorithm, card file format, or the gitignore confidentiality set.**

---

## 6. Per-dimension appendix (traceability: which proposals absorbed each dimension)

**D1 — Invocation & in-process feedback.** Absorbed: session-state header → B3; INGEST "you are here" map → folded
into B3 + B10; per-intent pre-flight checklist → folded into B7/B10 prose; mid-session position persistence → B7/B8;
strengthen safety default + explicit routing → B1/B3. Deferred: `flow-check` engine backstop → P2-1; echo ingest-check
readiness → covered by B2 (translate) rather than a separate line.

**D2 — Task & memory management.** Absorbed: CONTEXT.md digest → B8; always-leave-a-pointer → B7; STATUS last-session
recap → B8; orphan reconcile → B9; learning-records firing → P1-3 (detail layer behind CONTEXT). Deferred: `track_kind`
→ P2-2.

**D3 — Content & teaching quality.** Absorbed: pedagogy-SELECTION rule → B6 (P0); worked-examples → P1-1;
deliberate-practice → P1-2; metacognition → P1-4; dual-coding + interleaving → P1-5; productive-failure → P2-3;
de-dup card-derivation → P1-6. (Selection rule is P0 because "tutor for everything" is the realistic default failure;
the new method files it leans on are P1 and the rule degrades to tutor/active-recall until they exist.)

**D4 — UX & 小白化.** Absorbed: first-run onboarding → B4; strip vocabulary → B1; translate blockers → B2; silent
defaults → B4; teach-me/quiz-me reframe → B5; README re-lead → C3; plain status next-step → folded into B4/A2.
Correction: profile.md template EXISTS (`profile.example.md`); the real fix is activation + de-jargon → C2.

**D5 — Adversarial maturity.** Absorbed: session-leaves-a-trace → A1 + B7; 5-min first-win → B4; re-engagement surface
→ A2 + C3; clean live vault + hygiene → C1 + B9; first-run checklist → C3; show retention working → A3; trim INGEST →
B10; freeze backlog → C4; don't build FSRS weights → P2-4. This dimension sets the maturity bar used in §1.

---

## 7. Definition of done for "mature & usable"

The plan is complete when, with P0 merged: (1) an empty vault greets a new user and reaches a taught concept + ≥1
card in one short session; (2) `session-check` makes it impossible to silently end a session with no card and no
reason; (3) every status surface leads with the due count and RESUME reconstructs context from CONTEXT.md; (4)
`progress` shows the 3 retention numbers; (5) no engine jargon reaches the user; (6) the deferred backlog is frozen.
The human stickiness target — one user, one track, ≥10 cards, ≥3 review days — is then a usage milestone, not a build
milestone.
