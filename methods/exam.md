---
name: exam
description: >-
  Track MODE (not a per-turn pedagogy) for learning toward a dated, scored target — an exam or
  certification. Syllabus-driven and deadline-aware: diagnose → build a syllabus of modules →
  teach each module (reusing tutor / worked-examples) → quiz (active-recall + FSRS) → periodic
  mocks → a readiness read toward the exam date. Reuses the whole engine; adds no new state.
---

# exam — learning toward a dated, scored target

Use this when the learner has a **deadline and a score/pass bar** (IELTS, a cert, a course final),
not open-ended accumulation. It composes the existing pedagogies into a syllabus → study → quiz →
mock loop, and keeps the deadline in view. It is a *mode*: pick the right per-concept pedagogy
(`tutor` for theory, `worked-examples` for problem types, `deliberate-practice` for a performable
sub-skill) module by module.

## Setup (once per track)
- Create the track with `--mode exam`. **Put the exam date in the track's `deadline`** — the status
  board and `plan-day` then treat it as the urgency it is.
- Ground it in MISSION.md: the *target* (e.g. "IELTS overall 7.0, writing ≥6.5, by Oct 12") and the
  real why. Concrete bar over "do well".
- Lay out a **syllabus**: the exam's sections/modules. Write it into `plan.md` as the map (a
  checklist of modules with rough status). This is the spine RESUME and planning read.

## The loop
1. **Diagnose** the learner's current level per module (a quick baseline). Mark each module
   strong / shaky / unseen in `plan.md` + CONTEXT.md.
2. **Teach the weakest mission-relevant module** with the fitting pedagogy (don't default tutor for
   problem-solving — use worked-examples; for a timed skill, deliberate-practice).
3. **Quiz to retain** — distil cards from what was worked through; `active-recall` + FSRS schedule
   the spacing toward the date. Past-paper question types make excellent L2/L3 cards.
4. **Mock periodically** — a timed run under exam conditions; record the score in CONTEXT.md +
   a dated `learning-records/` entry. Mocks are the real readiness signal.
5. **Read readiness toward the date** — per module: covered? cards graduating (see `progress`)?
   last mock score vs bar? Spend remaining time by *gap × weight × days-left*. Be honest — a rough
   readiness read beats false confidence. (A precise score-conversion is exam-specific and out of
   scope; report mock scores + coverage, don't fabricate a single number.)

## Composes with
- `learner-model` (where they are per module), `learning-science` (mission, ZPD, storage),
  `active-recall` (card derivation + the review loop), `worked-examples` / `deliberate-practice`
  (problem & skill modules). The deadline lives in the engine (`deadline`), so `plan-day` already
  prioritizes an approaching exam.

## Anti-patterns
- Teaching breadth evenly while a deadline looms — triage by gap and weight.
- Tutor-lecturing problem types that need worked examples + practice.
- "Feeling ready" with no mock — schedule mocks; they're the ground truth.
- Inventing a precise readiness percentage; report what's measured (coverage, graduated cards, mock).
