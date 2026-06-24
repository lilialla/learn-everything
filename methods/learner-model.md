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
| `over-confident` | Probe a boundary where the simple story breaks — surface the gap they're skipping. Up-shift move: **ask them to find where the rule breaks** ("when does this stop being true? give me a case it gets wrong"). |
| Overwhelmed / high load | Shrink the step, drop jargon, give one worked example, slow down. |
| Bored | Increase challenge or connect to something they care about; don't re-explain what they have. Up-shift move: **pose an L3 transfer task** — a novel case where the simple model predicts wrong; ask what actually happens. |

For the `solid` / `bored` / `over-confident` rows, load **`methods/elaboration.md`** — the
up-shift pedagogy (transfer tasks, find-the-break, elaborative interrogation, compression,
interleaving), the mirror of how tutor/socratic catch the struggling learner.

## Updating the model

Treat each learner turn as evidence that *revises* your estimate — don't anchor on a first
impression. A confident wrong answer downgrades grasp to `over-confident`, not `solid`. A
good answer to a hard question upgrades it. If your prediction of what they'd say keeps being
wrong, your model is off — widen your questions to recalibrate rather than pushing forward.

## Persistence (the silent read must leave a trace — not optional)

The per-turn inference is silent, but a CONFIRMED misconception or sticking point must be
**persisted**, or it's lost the moment the conversation ends:

- **Always** record a confirmed sticking point in the track's `tracks/<id>/CONTEXT.md` under
  "Known sticking points" (the rolling memory RESUME reads first).
- When a misconception is genuinely **corrected** during the session, also write a dated
  `tracks/<id>/learning-records/NNNN-slug.md` (1–3 sentences: what was wrong, what's right now,
  why it matters next time) — these are the durable, traceable insights behind the rolling digest.
- A recurring sticking point is prime **review-card** material — flag it for the card pass.
- If a `profile.md` exists at the repo root, read it for durable traits (background, prior
  knowledge, language, pace) and use them as priors.

The live per-turn inference drives teaching; persistence is what makes "where I went wrong"
survive into the next session. Skipping it is the silent-gap failure.

## Anti-patterns

- Printing the analysis at the learner ("I sense you are confused about…") — keep it silent.
- Modeling the *topic* instead of the *learner*: the question is "where is THIS person," not
  "what does the textbook say next."
- Anchoring: refusing to downgrade grasp after contradicting evidence.
- Over-inferring from one turn — when unsure, ask a diagnostic question instead of guessing.
