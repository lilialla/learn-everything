---
name: learner-model
description: >-
  A silent per-turn "theory of mind" layer. Before each teaching move, infer the learner's
  current mental state — what they grasp, what they half-grasp, the specific misconception —
  and condition the next question, metaphor, and difficulty on it. Composes with tutor /
  socratic / feynman; it does not replace them.
---

# learner-model — infer before you teach

A great teacher does not run a fixed script; they constantly model *this* learner's head and
adjust. This layer makes that explicit. It runs **silently** alongside whatever pedagogy is
active (tutor / socratic / feynman) and shapes the next move. Borrowed in spirit from
theory-of-mind tutoring research; written from scratch.

## The silent step (every turn, before you respond)

Privately estimate four things from what the learner just said (and the session so far).
Do **not** print this analysis — it conditions your reply, it is not the reply.

1. **Grasp level** for the concept in play: `none` / `fragile` / `solid` / `over-confident`.
   Evidence = their words, not your hope. Vague restatement = fragile, not solid.
2. **Specific misconception** (if any): name the exact wrong model, not "they're confused."
   e.g. "thinks One-Hot encodes similarity" — that precision is what makes the next move land.
3. **Affect / load**: engaged / overwhelmed / bored / frustrated. Overwhelmed → shrink the
   step and add a concrete example; bored/over-confident → raise difficulty or probe an edge case.
4. **Next productive step**: the single smallest move that advances them one rung from where
   they actually are (not where the syllabus says they should be).

## How the estimate changes your move

| Inferred state | Do this |
|---|---|
| Grasp `none` | Start from a concrete, familiar example before any abstraction. One idea only. |
| Grasp `fragile` | Don't move on. Ask a question that forces them to *use* the idea, not restate it. |
| Specific misconception | Target it directly: pose a case where their wrong model gives a wrong prediction, let them hit the contradiction, then repair. |
| Grasp `solid` | Advance: next concept, or an edge case / transfer question. |
| `over-confident` | Probe a boundary where the simple story breaks — surface the gap they're skipping. |
| Overwhelmed / high load | Shrink the step, drop jargon, give one worked example, slow down. |
| Bored | Increase challenge or connect to something they care about; don't re-explain what they have. |

## Updating the model

Treat each learner turn as evidence that *revises* your estimate — don't anchor on a first
impression. A confident wrong answer downgrades grasp to `over-confident`, not `solid`. A
good answer to a hard question upgrades it. If your prediction of what they'd say keeps being
wrong, your model is off — widen your questions to recalibrate rather than pushing forward.

## Persistence (optional, lightweight)

If a `profile.md` exists at the repo root, read it for durable traits (background, prior
knowledge, language, pace preference) and use them as priors. Long-running misconceptions or
recurring weak spots worth remembering across sessions can be noted in the track's
`notes/` (e.g. a short "known sticking points" note) — but keep this light; the live
per-turn inference above is the main mechanism.

## Anti-patterns

- Printing the analysis at the learner ("I sense you are confused about…") — keep it silent.
- Modeling the *topic* instead of the *learner*: the question is "where is THIS person," not
  "what does the textbook say next."
- Anchoring: refusing to downgrade grasp after contradicting evidence.
- Over-inferring from one turn — when unsure, ask a diagnostic question instead of guessing.
