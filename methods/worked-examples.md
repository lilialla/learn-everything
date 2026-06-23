---
name: worked-examples
description: >-
  The default pedagogy for PROCEDURAL material — math, coding, STEM problem-solving, any
  "how to *do* X" skill where tutor (built for knowledge) leaves a gap. Grounded in Cognitive
  Load Theory: a novice learns a procedure faster by *studying* a fully worked example than by
  floundering through an unscaffolded problem. Runs the I-do → we-do → you-do fade, completion
  problems, and self-explanation prompts, then fades guidance as skill grows (expertise
  reversal). Composes with learner-model (read the fade speed) and active-recall (harvest stumbles).
---

# worked-examples — show the work, then fade it

Use this when the goal is to *do* something, not just understand it: solve the integral, write
the function, balance the equation, apply the algorithm. A novice facing a blank problem spends
all their working memory searching for *what to do next*, leaving none for *learning the method* —
this is the **worked-example effect** (Sweller & Cooper, 1985): studying a complete solution first
beats unguided problem-solving for novices. So you lead with the answer worked out, then hand the
pen over one step at a time. tutor is for knowledge; this is for procedure — pick it for STEM.

**Respond in the user's language.** Keep canonical terms/notation as the field writes them.

## The fade (the spine of this method): I-do → we-do → you-do

1. **I do** — *study a worked example.* Present one complete, correct solution to a representative
   problem, every step shown. Don't race: at each step say *what* you did and *why this step, now*.
   The learner's job here is to study, not solve — call that out so they don't feel passive.
2. **We do** — *completion problem.* Give a similar problem **partially worked**: you do the first
   steps, blank out the rest, and the learner fills only the gap. This is the completion effect
   (van Merriënboer) — far less load than a blank page, far more learning than just watching.
3. **You do** — *solo attempt.* A fresh similar problem, no scaffold. They drive; you only react.

Move along this fade as competence shows, not on a timer. Fade *backward* (you-do → we-do) the
moment they stall — a stall means the support was pulled too early.

## Self-explanation (the multiplier — use throughout)

At each step of I-do and we-do, ask the learner to explain the step, not just accept it:
"**why** this step here?", "what would break if we skipped it?", "which rule licenses this move?".
Self-explanation (Chi et al.) is the single biggest amplifier of worked examples — learners who
explain steps to themselves transfer far better. A learner who can re-derive *why* owns the
procedure; one who only pattern-matches the surface will fail the first novel variant.

## The per-problem loop (run this for EACH problem)

1. **Frame** — name the problem type and what "done" looks like (the target form of the answer).
2. **Demonstrate or scaffold** — depending on where they are on the fade: fully work it (I-do),
   partially work it (we-do), or hand it over (you-do).
3. **Self-explain** — make them justify the load-bearing step(s) in their own words.
4. **Attempt + react** — let them produce the next step / the rest / the whole thing. Diagnose the
   *first* wrong move precisely (per learner-model) — that's where the method broke, not the later
   symptoms. Re-teach that one step, don't redo the whole solution.
5. **Advance the fade** — clean success → less scaffold next problem; a stall → more scaffold.

## Fade faster as they improve (expertise reversal — important)

The worked-example advantage **inverts** with expertise (Kalyuga's expertise-reversal effect):
once the learner has the schema, studying yet another full solution is redundant and boring — for
them, *solving* is now the better practice. So watch for fluency and **fade aggressively**: drop to
completion problems, then to solo problems, then to harder/novel variants. Don't keep narrating
worked examples to someone who's already pattern-fluent — that's the procedural analogue of
re-explaining what they already know. (Hand off the up-shift to `methods/elaboration.md`.)

## Compose with learner-model (set the fade speed)

Run `methods/learner-model.md` silently every turn; it controls *how fast you fade*:
- grasp `none` → stay in I-do, shrink the example, one method only.
- grasp `fragile` → completion problems with a narrowing gap; don't jump to solo yet.
- grasp `solid` / `bored` → fade to solo and novel variants fast (expertise reversal); up-shift via
  elaboration.
- specific misconception → don't just re-demo; pose a problem where their wrong procedure yields a
  visibly wrong answer, let them hit it, then repair that step.

## Compose with active-recall (harvest the stumbles into cards)

The wrong steps are gold. At a natural pause, distill what they actually stumbled on into cards via
`add-card`, following active-recall.md as the single source for card-derivation and its quality gate:
**L1** the fact/rule a step depends on; **L2** *why* that step is needed / when it applies (the
self-explanation, compressed); **L3** a transfer problem — a novel case where the same procedure
applies but the surface differs. Procedures decay without retrieval; the card deck is the safety net
under the skill. Offer 2–4, save only on a yes.

## Live notes & progress

Maintain the running note at `tracks/<id>/notes/<date>-<topic>.md`: the problem type, the worked
solution, the key self-explanation, and where they stalled — written FOR the learner as a reusable
worked reference, with `[[wikilinks]]`. At session end, `registry.py log` what was covered and set
`next_action` to the next problem type or the next rung of the fade, and update `plan.md`.

## Anti-patterns

- Throwing a blank problem at a novice "to build grit" — that's cognitive overload, the exact thing
  worked examples exist to prevent.
- Narrating solutions forever — past the schema, watching is boredom; let them solve (expertise reversal).
- Demoing without self-explanation — silent watching builds pattern-matching, not transferable method.
- Re-solving the whole thing after one wrong step — find and repair the *first* broken step only.
- Only ever using near-identical problems — without a novel variant (L3), you've trained surface
  pattern-matching, not the procedure.
