# learn-everything — Ecosystem Scan & Integration Plan

> Date: 2026-06-22
> Synthesized from 6 parallel scout reports (Claude/Codex learning skills; Obsidian agent hosts + SRS plugins; FSRS engine libs; LLM-tutor pedagogy; PKM/note-graph frameworks; flashcard/Anki-export tooling).
> Network note: github.com WebFetch is policy-blocked; all metadata below was verified via `gh api` / `gh search` by the scouts (snapshot 2026-06-22).

## TL;DR — the strategic read

The learning-skill ecosystem is **thin on real pedagogy and thick on Anki plumbing**. ~20 near-identical `anki-mcp-server` wrappers exist; only a couple are worth tracking. The genuine, transferable value for learn-everything is concentrated in a handful of small skills/research repos that encode **knowledge-as-data** (tutoring loops, card-quality rubrics, learner modeling) — which is exactly learn-everything's METHODS-layer design. Almost everything is a **BORROW (idea/prompt)** or **INTEROPERATE (optional companion)**, not an **ADOPT (dependency)**, because the project's invariants are: zero-pip portable CORE, markdown-files-are-truth, skill-first host adapter.

**Our genuine, unfilled differentiator: cross-track orchestration + live tutor + native Obsidian one-app.** No surveyed project does multi-track learning-OS orchestration with FSRS-as-safety-net under a live tutor. That is the part to **build**.

---

## Deduped project table

Stars/license/last-active as verified by scouts on 2026-06-22. Sorted by action then fit.

| Project | Stars | License | Last active | Action | Fit | One-liner |
|---|---|---|---|---|---|---|
| [open-spaced-repetition/py-fsrs](https://github.com/open-spaced-repetition/py-fsrs) | 441 | MIT | 2026-03 | BORROW (test oracle, dev/CI only) | high | Canonical pure-Python FSRS reference impl |
| [maaarcooo/claude-skills (learn)](https://github.com/maaarcooo/claude-skills/tree/main/learn) | 6 | NOASSERTION | 2026-06 | BORROW (pedagogy) | high | Diagnose-then-teach Claude `learn` skill |
| [doasfrancisco/anki-skill](https://github.com/doasfrancisco/anki-skill) | 28 | none | 2026-02 | BORROW (card-quality rubric) | high | Anki skill with opinionated card-quality rulebook |
| [jalliet/flashcards](https://github.com/jalliet/flashcards) | 11 | none | 2026-02 | BORROW (L1/L2/L3 framework) | high | Science-of-learning 3-layer card generator |
| [eth-lre/PedagogicalRL](https://github.com/eth-lre/PedagogicalRL) | 39 | none | 2025-12 | BORROW (Socratic rubric) | high | EMNLP'25 tutor-not-answer RL rubric |
| [plastic-labs/tutor-gpt](https://github.com/plastic-labs/tutor-gpt) | 906 | GPL-3.0 | 2026-02 | BORROW (learner-model loop, ideas only) | high | Theory-of-Mind learner-modeling tutor |
| [HKUDS/DeepTutor](https://github.com/HKUDS/DeepTutor) | 24895 | Apache-2.0 | 2026-06 | BORROW (memory hierarchy + mastery gate) | high | Agent-native tutoring OS, L1/L2/L3 memory |
| [basicmachines-co/basic-memory](https://github.com/basicmachines-co/basic-memory) | 3273 | AGPL-3.0 | 2026-06 | BORROW (note-graph schema) + INTEROPERATE | high | Local-first markdown KB w/ typed entity/relation graph over MCP |
| [YishenTu/claudian](https://github.com/YishenTu/claudian) | 13071 | MIT | 2026-06 | INTEROPERATE (primary host) | high | Embeds Claude Code in Obsidian; vault = agent cwd; MCP |
| [st3v3nmw/obsidian-spaced-repetition](https://github.com/st3v3nmw/obsidian-spaced-repetition) | 2436 | MIT | 2026-06 | BORROW (card markdown syntax) | high | De-facto Obsidian SRS plugin (FSRS/SM-2) |
| [kerrickstaley/genanki](https://github.com/kerrickstaley/genanki) | 2636 | MIT | 2024-12 | ADOPT (optional offline-export adapter) | high | Pure-Python `.apkg` deck generator |
| [kitschpatrol/yanki](https://github.com/kitschpatrol/yanki) | 51 | MIT | 2026-05 | INTEROPERATE/BORROW (md→Anki sync) | high | Markdown→Anki sync via AnkiConnect (stable IDs) |
| [ankimcp/anki-mcp-server](https://github.com/ankimcp/anki-mcp-server) | 344 | MIT | 2026-06 | INTEROPERATE (optional Anki bridge) | medium | Leading MIT MCP server for Anki |
| [open-spaced-repetition/obsidian-spaced-repetition-recall](https://github.com/open-spaced-repetition/obsidian-spaced-repetition-recall) | 206 | MIT | 2026-06 | BORROW (JSON sidecar schema) | medium | Fork moving SRS state to JSON sidecar |
| [open-spaced-repetition/ts-fsrs](https://github.com/open-spaced-repetition/ts-fsrs) | 691 | MIT | 2026-06 | INTEROPERATE (only if TS surface built) | medium | Official TS FSRS port |
| [open-spaced-repetition/fsrs-optimizer](https://github.com/open-spaced-repetition/fsrs-optimizer) | 105 | BSD-3 | 2026-02 | BORROW (optional offline weight-fit) | medium | PyTorch fitter for personalized FSRS weights |
| [iansinnott/obsidian-claude-code-mcp](https://github.com/iansinnott/obsidian-claude-code-mcp) | 307 | 0BSD | 2025-06 (stale) | INTEROPERATE (outside-in fallback) | medium | Exposes vault to external Claude Code over MCP |
| [tuan3w/obsidian-vault-agent](https://github.com/tuan3w/obsidian-vault-agent) | 27 | MIT | 2026-03 | BORROW (ingestion prompts) | medium | Claude Code plugin: sources→connected Obsidian notes |
| [Ljyustc/SocraticLM](https://github.com/Ljyustc/SocraticLM) | 175 | none | 2025-03 | BORROW (Dean-Teacher-Student self-audit) | medium | NeurIPS'24 Socratic math multi-agent scaffold |
| [ECNU-ICALK/SocraticMath](https://github.com/ECNU-ICALK/SocraticMath) | 13 | none | 2026-04 | BORROW (question-type taxonomy) | medium | CIKM'24 Socratic question taxonomy |
| [thiswillbeyourgithub/AnkiAIUtils](https://github.com/thiswillbeyourgithub/AnkiAIUtils) | 861 | AGPL-3.0 | 2026-06 | BORROW (card heuristics, ideas only) | medium | Mature AI card-enhancement suite |
| [supermemoryai/supermemory](https://github.com/supermemoryai/supermemory) | 27297 | MIT | 2026-06 | INTEROPERATE (optional retrieval) | medium | MIT local-capable memory/context engine |
| [mem0ai/mem0](https://github.com/mem0ai/mem0) | 59105 | Apache-2.0 | 2026-06 | BORROW (fact-extraction loop) | medium | Self-improving memory layer for agents |
| [brianpetro/obsidian-smart-connections](https://github.com/brianpetro/obsidian-smart-connections) | 5191 | NOASSERTION (claims MIT) | 2026-06 | INTEROPERATE (companion plugin) | medium | Local-embedding related-notes for Obsidian |
| [RahulM4/dsa-coach](https://github.com/RahulM4/dsa-coach) | 0 | none | 2026-05 | BORROW (weakness→generate loop) | medium | SM-2 + generated practice + Socratic, DSA domain |
| [yarikleto/claude-teacher-plugin](https://github.com/yarikleto/claude-teacher-plugin) | 2 | none | 2026-04 | BORROW (prompt phrasing) | medium | Claude Code tutor: Socratic+Feynman+spaced-rep |
| [loftiskg/anki-claude-code-skill](https://github.com/loftiskg/anki-claude-code-skill) | 0 | MIT | 2026-04 | BORROW (evidence-based card rubric) | medium | Claude Code Anki skill w/ flashcard-science rubric |
| [GeminiLight/awesome-ai-llm4education](https://github.com/GeminiLight/awesome-ai-llm4education) | 193 | none | 2026-06 | SKIP-but-track (reading index) | low | Curated LLM-for-education paper list |
| [open-spaced-repetition/fsrs-rs](https://github.com/open-spaced-repetition/fsrs-rs) | 386 | BSD-3 | 2026-06 | SKIP-but-note (tie-breaker authority) | low | Rust FSRS, the engine behind Anki |
| [open-spaced-repetition/fsrs4anki](https://github.com/open-spaced-repetition/fsrs4anki) | 3991 | MIT | 2026-03 | SKIP-but-note (docs/semantics ref) | low | Flagship Anki FSRS scheduler (not a lib) |
| [glowingjade/obsidian-smart-composer](https://github.com/glowingjade/obsidian-smart-composer) | 2295 | MIT | 2026-02 | SKIP (not active / not CC runner) | low | MCP-capable Obsidian chat, dev paused |
| [logancyang/obsidian-copilot](https://github.com/logancyang/obsidian-copilot) | 7257 | AGPL-3.0 | 2026-06 | SKIP (positioning only) | low | In-vault AI chat; AGPL; not a skill loader |
| [khoj-ai/khoj](https://github.com/khoj-ai/khoj) | 35245 | AGPL-3.0 | 2026-03 | SKIP (owns its store) | low | Self-host AI second brain (Postgres+vector) |
| [reorproject/reor](https://github.com/reorproject/reor) | 8562 | AGPL-3.0 | 2025-05 (archived) | SKIP (archived) | low | Local PKM auto-linking notes |
| [QuivrHQ/quivr](https://github.com/QuivrHQ/quivr) | 39163 | Commons-Clause | 2025-07 | SKIP (not OSI-OSS) | low | RAG-over-files framework |
| [nhaouari/obsidian-textgenerator-plugin](https://github.com/nhaouari/obsidian-textgenerator-plugin) | 1956 | MIT | 2026-05 | SKIP (wrong abstraction) | low | Template text-gen for Obsidian |
| anki-mcp-server clones (nailuoGG 243★, scorzeth 183★, CamdenClark 81★, …) | — | mixed/none | 2026-06 | SKIP (saturated/redundant) | low | ~15-20 interchangeable AnkiConnect MCP bridges |

**Dropped as junk/stale/no-value** (scout-filtered, not surfaced): CAHLR/OATutor-LLM-Learner (3★, stale), Geralt-Targaryen/Awesome-Education-LLM (stale 2024-09), gpoesia/socratic-tutor (dead 2023), pleyva2004/claude-skill-study-paper (0★, ML-paper-only, idea-level only), go-fsrs (wrong language), AnnA_Anki_neuronal_Appendix (AGPL, not an FSRS engine), Logseq (full app, not a lib), dozens of <10★ flashcard-generator clones. **Unverifiable closed plugins** (LearnKit, True Recall, SRAI) returned `[]` from `gh search` — no public repo, so license/maintenance unverifiable; do not adopt, but note **True Recall's "local SQLite + FSRS-6 + Anki import/export" is our strongest conceptual competitor** — worth a manual look before locking `review-state.json` schema.

---

## Per-component plan

### 1. ENGINE — `scripts/fsrs.py`

**Recommendation: KEEP zero-dep hand-rolled. Add [py-fsrs](https://github.com/open-spaced-repetition/py-fsrs) as a dev/CI-only TEST ORACLE. Do NOT adopt it as a runtime dependency.**

The tradeoff is decisive given the project's stated invariant (`fsrs.py` header already says "stdlib only" and explicitly *defers* numeric parity to py-fsrs):
- **Adopting py-fsrs as runtime** = breaks the pip-free portable promise for ~zero user-facing benefit. Every FSRS Python lib is pip-installable; the runtime cost (a dependency) is real, the accuracy gain at runtime is invisible to learners.
- **py-fsrs as oracle** = converts our current behavioral-only tests into **reference-accurate parity tests** with zero runtime cost. Pin a py-fsrs version, generate reference `(stability, difficulty, next-interval)` across a grid of `(rating, elapsed_days, state)`, assert our output matches within tolerance. This directly closes the "NUMERIC PARITY DEFERRED" caveat in our own file header.
- Secondary: cross-check our `DEFAULT_WEIGHTS` (w[0..20]) against py-fsrs's current FSRS-6 defaults.
- Authority tie-breaker if py-fsrs and the wider ecosystem ever disagree: [fsrs-rs](https://github.com/open-spaced-repetition/fsrs-rs) (the engine inside Anki). [fsrs4anki](https://github.com/open-spaced-repetition/fsrs4anki) wiki is the best plain-language doc for weight semantics + edge cases (same-day reviews, lapses) — use when writing fixtures.
- **Later/optional**: [fsrs-optimizer](https://github.com/open-spaced-repetition/fsrs-optimizer) for an opt-in offline "optimize my schedule" command once a user has enough reviews in `review-state.json`. Strictly offline (pulls torch) — never CORE.
- If/when a TS Obsidian surface is ever built, use [ts-fsrs](https://github.com/open-spaced-repetition/ts-fsrs) rather than re-porting FSRS in JS — but then a cross-engine parity test becomes mandatory.

> Honest call: **reuse the algorithm as ground truth, don't rebuild the verification.** Keep the runtime; harden the test.

### 2. METHODS — pedagogy layer (`methods/*.md`)

This is where the richest borrows live. All sources here are license-gated (GPL / none / NOASSERTION), so **borrow IDEAS and PROMPTS only, rewrite in our own words, cite the papers; vendor no files.** Only DeepTutor (Apache-2.0) is clean for a literal snippet port.

Concrete additions:

1. **`methods/socratic.md` — tighten with an anti-leakage tiered-hint rule.** From [PedagogicalRL](https://github.com/eth-lre/PedagogicalRL)'s three named axes (Socratic questioning / helpful scaffolding / solution-withholding): encode "never reveal the answer before the learner attempts; escalate hints in tiers; self-check each turn for leakage." Add [SocraticMath](https://github.com/ECNU-ICALK/SocraticMath)'s **question-type taxonomy** (clarify / probe assumptions / probe evidence / probe implications / counter-example) as a menu the tutor rotates through so it stops repeating one pattern.

2. **NEW `methods/learner-model.md` — the one pedagogical layer we're missing.** From [tutor-gpt](https://github.com/plastic-labs/tutor-gpt) (Theory-of-Mind): before each tutoring turn, run a silent step that infers the learner's current mental state / misconception from their last response, then condition the next question/metaphor/difficulty on it. This is the single highest-leverage pedagogy borrow — `tutor.md` currently adapts reactively ("if they're lost, re-teach") but has no explicit learner-state inference step. **GPL — ideas/prompts only, zero code.**

3. **`methods/tutor.md` + a hidden self-audit.** From [SocraticLM](https://github.com/Ljyustc/SocraticLM)'s Dean-Teacher-Student scaffold: have the host LLM internally role-play a "Dean" that audits whether the drafted turn was genuinely Socratic (led with a question, withheld the answer) before emitting it. Cheap hidden review step.

4. **Mastery gating idea for cross-track progression.** From [DeepTutor](https://github.com/HKUDS/DeepTutor): a **hard per-type mastery gate** is a stronger progression signal than FSRS due-date alone. Consider gating `next_action`/track advancement on demonstrated per-concept mastery, not just spaced-rep timing. Also borrow its **persona presets** (peer / teacher / research-assistant) as method variants.

5. **Validation, not new method:** [maaarcooo/learn](https://github.com/maaarcooo/claude-skills/tree/main/learn) (diagnose-first, one-question-one-scaffold, explicit session-end criteria) and [yarikleto/claude-teacher-plugin](https://github.com/yarikleto/claude-teacher-plugin) (Socratic+Feynman+spaced-rep on the exact same Claude-Code surface) both prove our product shape. Read for concrete teacher phrasings to fold into `feynman.md`/`active-recall.md`; both are tiny/unlicensed — rewrite.

> Honest call: **build our methods, but borrow these five well-tested moves.** The learner-model layer is the real gap; everything else is sharpening.

### 3. NOTES / MOC / QUERY

**Recommendation: keep it simple (flat markdown + `[[wikilinks]]` + `plan.md` MOC) for now; BORROW the [Basic Memory](https://github.com/basicmachines-co/basic-memory) typed schema as the upgrade path; INTEROPERATE via Obsidian companion plugins for semantic recall. Do NOT adopt a vector/DB "second brain" — every one of them owns the store, which breaks files-are-truth.**

- Basic Memory is our closest philosophical sibling (markdown-as-source-of-truth + MCP + Obsidian-compatible). When flat notes start needing real queries, **clean-room borrow its entity / typed-observation / typed-relation model** to turn `plan.md` MOCs into a queryable graph. AGPL — study + interoperate + mirror conventions, never vendor code.
- For "what did I learn about X across all tracks" semantic recall beyond the FSRS card net: recommend [Smart Connections](https://github.com/brianpetro/obsidian-smart-connections) (local, no API key) as a **co-installed companion plugin** rather than building our own embeddings. Optionally [supermemory](https://github.com/supermemoryai/supermemory) (MIT) or [mem0](https://github.com/mem0ai/mem0) (Apache) as optional retrieval backends — always optional, never required.
- BORROW [mem0](https://github.com/mem0ai/mem0)'s "extract salient facts from conversation → store as atomic memories" prompt pattern for our "tutor session → notes/cards as byproduct" loop. (Skip its runtime — it's a vector store.)

> Honest call: **don't rebuild semantic note-linking — Smart Connections does it better.** Keep our notes flat + Obsidian-native; reach for the Basic Memory schema only when query needs outgrow MOCs.

### 4. CARD INGEST — `methods/active-recall.md` + card distillation

**Recommendation: do NOT build a card-generation engine (commoditized). BORROW a card-QUALITY rubric to gate distillation; add TWO optional Anki export paths.**

Card-quality rubric (mine, rewrite, gate the "distill cards" step):
- **L1/L2/L3 layering** from [jalliet/flashcards](https://github.com/jalliet/flashcards): L1 recall (facts/formulas) / L2 understanding (connections/intuition) / L3 boundaries (edge cases/limits) — forces coverage past rote. Pairs with feynman + active-recall.
- **Atomicity + duplicate-check + leech-awareness** from [doasfrancisco/anki-skill](https://github.com/doasfrancisco/anki-skill): one fact per card (split on "and"), short unambiguous front, visual-over-prose, check-for-duplicate-before-create.
- **Refusal policy** (don't atomize proofs/worked examples) from jalliet; **evidence-based rubric** from [loftiskg/anki-claude-code-skill](https://github.com/loftiskg/anki-claude-code-skill) (MIT); deeper heuristics (mnemonics, reformulating weak cards) from [AnkiAIUtils](https://github.com/thiswillbeyourgithub/AnkiAIUtils) (AGPL — ideas only).

Anki interop (because our cards are already atomic markdown with stable IDs):
- **ONLINE / LLM-native:** the host LLM calls an AnkiConnect MCP ([ankimcp/anki-mcp-server](https://github.com/ankimcp/anki-mcp-server), MIT, active) to push distilled cards into the user's real Anki mid-session. Matches the host-adapter philosophy. Document as optional.
- **OFFLINE / no Anki running:** [genanki](https://github.com/kerrickstaley/genanki) (MIT, pure-Python) in an **optional adapter** (never CORE — it's pip) to emit `.apkg`. Derive stable GUIDs from our card IDs for idempotent re-export. Alternatively [yanki](https://github.com/kitschpatrol/yanki) (MIT, TS) for md→Anki sync with stable note IDs — borrow its folder→deck mapping.
- For Obsidian-native review without any Anki: **BORROW [st3v3nmw/obsidian-spaced-repetition](https://github.com/st3v3nmw/obsidian-spaced-repetition) card markdown syntax** (`Q::A`, multi-line `?`, cloze `==..==`) so `cards/*.md` render as reviewable cards in-vault with no custom UI. Study [obsidian-spaced-repetition-recall](https://github.com/open-spaced-repetition/obsidian-spaced-repetition-recall)'s **JSON sidecar schema** to keep our `review-state.json` import/export-friendly.

> Honest call: **reuse Anki export (genanki/MCP), don't write an exporter; reuse a card-quality rubric, don't invent one.**

### 5. OBSIDIAN ONE-APP ADAPTER — making "one app = Obsidian" real

**Primary host = [Claudian](https://github.com/YishenTu/claudian) (MIT, 13k★, pushed daily).** It embeds Claude Code in Obsidian, makes the **vault the agent's working directory** (read/write/search/**bash**/multi-step), and connects external MCP servers. learn-everything's `skills/learn/SKILL.md`, stdlib CORE (`fsrs.py`, `registry.py`) and `tracks/` folders run unchanged inside the vault Claudian opens as cwd. The split-screen tutor UX (source/notes left, agent right) is exactly what Claudian renders.

- **Fallback (outside-in):** [iansinnott/obsidian-claude-code-mcp](https://github.com/iansinnott/obsidian-claude-code-mcp) (0BSD) for users who drive learn-everything from an **external** Claude Code terminal against their vault. Stale (~2025-06) — verify it still connects before recommending.
- **Native review surface:** install [st3v3nmw/obsidian-spaced-repetition](https://github.com/st3v3nmw/obsidian-spaced-repetition) so cards review natively; keep our `fsrs.py` authoritative.
- **Companion (optional):** [Smart Connections](https://github.com/brianpetro/obsidian-smart-connections) for semantic related-notes.

**Install story:** Obsidian → install Claudian + obsidian-spaced-repetition (+ optionally Smart Connections) → clone learn-everything into (or alongside) the vault → open the vault in Claudian → invoke the `learn` skill. One app, split screen.

**OPEN QUESTION (must resolve before claiming the one-app story works): does Claudian's embedded Claude Code actually execute our Python scripts via Bash?**
- Claudian advertises bash/multi-step agent capabilities, and our CORE is plain `python3 scripts/*.py`. *In principle* it should run. **But this is unverified** — embedded-runtime sandboxing, the Python the embedded agent sees (PATH/venv), and whether Bash is enabled by default are all unknown.
- **Action: a 30-minute spike** — open the vault in Claudian and run `python3 scripts/fsrs.py schedule ...` and `python3 scripts/registry.py log ...` from the embedded agent. If Bash/Python don't work in-vault, the fallback is: (a) the iansinnott outside-in MCP path (external terminal has real Bash), or (b) reimplement the thin CLI surface in TS as an Obsidian plugin command using [ts-fsrs](https://github.com/open-spaced-repetition/ts-fsrs) — which then forces the cross-engine parity test from §1.
- **Decide one authoritative FSRS writer.** Our `fsrs.py` and any Obsidian SRS plugin both schedule; if both write state they drift. Designate `fsrs.py` + `review-state.json` as source of truth and treat the plugin as a **review front-end only** (align card *syntax*, ignore its scheduler), OR delegate scheduling to the plugin and stop running ours in-vault. Pick one.

> Honest call: **reuse Claudian as host — do not build an Obsidian plugin** unless the Bash spike fails.

### 6. BUILD vs REUSE — crisp table

| Capability | Verdict | Why |
|---|---|---|
| FSRS-6 scheduler runtime | **BUILD (keep)** + reuse py-fsrs as oracle | Zero-dep invariant; parity test closes the accuracy gap |
| FSRS parameter optimization | **REUSE** (optional, fsrs-optimizer, offline) | Don't hand-roll torch fitting |
| Tutor / Socratic / Feynman methods | **BUILD** + borrow 5 moves | Our differentiator; sources are license-gated |
| Learner-model (ToM) layer | **BUILD** (borrow tutor-gpt pattern) | Genuine gap in our methods |
| Card-quality rubric | **REUSE** (borrow L1/L2/L3 + atomicity rules) | Well-solved; just encode as a gate |
| Card-generation engine | **DON'T BUILD** | Commoditized, dozens of clones |
| Anki export (`.apkg` / sync) | **REUSE** (genanki offline / AnkiConnect MCP online) | Mature, MIT; optional adapters only |
| Obsidian-native card review | **REUSE** (st3v3nmw plugin syntax) | Don't write a review UI |
| Semantic related-notes | **REUSE** (Smart Connections companion) | Better than we'd build |
| Typed note-graph / query | **BUILD later** (borrow Basic Memory schema) | Start flat; upgrade when MOCs outgrow |
| Obsidian agent host | **REUSE** (Claudian primary, MCP fallback) | Don't build a plugin |
| **Cross-track learning-OS orchestration** | **BUILD** | **Nobody does this — our core differentiator** |
| Per-concept mastery gating | **BUILD** (borrow DeepTutor idea) | Strengthens our orchestration |

---

## Do this next (prioritized)

1. **[Spike, <1d] Verify Claudian runs our Python via Bash in-vault.** The entire one-app story hinges on this. Run `fsrs.py`/`registry.py` from Claudian's embedded agent. Decide the FSRS-authoritative-writer question while you're there.
2. **[<1h] Add `methods/learner-model.md`** — the silent per-turn Theory-of-Mind inference step (borrow tutor-gpt pattern, rewrite). Highest-leverage pedagogy gap, fully under our control.
3. **[<1h] Harden `methods/socratic.md`** with the PedagogicalRL anti-leakage tiered-hint rule + SocraticMath question-type taxonomy menu.
4. **[<1h] Add a card-quality gate** to `methods/active-recall.md`: L1/L2/L3 layering + atomicity + duplicate-check + refusal policy (borrow jalliet/doasfrancisco/loftiskg rubrics, rewrite).
5. **[~1d, dev/CI] Add py-fsrs parity test.** Pin a version, generate a reference grid, assert `fsrs.py` matches within tolerance. Closes the "PARITY DEFERRED" caveat in our own header. py-fsrs stays dev-only.
6. **[<1h] Align `cards/*.md` to st3v3nmw card syntax** so cards review natively in Obsidian with no custom UI; document obsidian-spaced-repetition + Claudian as the recommended install.
7. **[later] Optional Anki export adapter** via genanki (offline `.apkg`) and/or an AnkiConnect MCP (online), kept strictly out of CORE.
8. **[later] Manually inspect True Recall / LearnKit** on obsidianstats before locking `review-state.json` schema — the only conceptual SRS competitors we couldn't verify via gh.

---

## License hygiene (carry into every borrow)

- **Safe to adopt/port verbatim (permissive):** py-fsrs, ts-fsrs, fsrs-rs (BSD-3), genanki, yanki, ankimcp, Claudian, st3v3nmw, recall-fork, Smart-Connections (claims MIT — verify LICENSE), supermemory, mem0, iansinnott (0BSD), loftiskg, vault-agent, DeepTutor (Apache).
- **Ideas/prompts ONLY, never vendor code:** tutor-gpt (GPL-3.0), AnkiAIUtils/AnkiGPT (AGPL-3.0), Basic Memory/Khoj/Copilot/Reor (AGPL — interoperate + mirror conventions, no code).
- **No LICENSE file = all-rights-reserved by default** (PedagogicalRL, SocraticLM, SocraticMath, doasfrancisco, jalliet, dsa-coach, claude-teacher-plugin, nailuoGG MCP): read for ideas, rewrite in our own words, cite — do not copy SKILL.md / prompt text.
- **NOASSERTION / non-OSS:** maaarcooo/learn (unclear), Quivr (Commons Clause = source-available, not OSS — skip).
