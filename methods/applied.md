---
name: applied
description: >-
  Track MODE (not a per-turn pedagogy) for learning by BUILDING something real — a project, not a
  syllabus or a source. The learner does the work; learning is captured as a byproduct: cards from
  the traps they hit, notes from what they built, concepts surfaced while doing. Reuses the whole
  engine; adds no new state.
---

# applied — learn by building

Use this when the goal is a **performable outcome via a real project** ("ship a small RAG app",
"automate my contract intake"), not reading a body of knowledge (that's `domain`) and not a dated
exam (that's `exam`). The project drives; teaching is just-in-time; the durable learning is the
trail of solved problems.

## Setup (once per track)
- Create the track with `--mode applied`. MISSION.md = the concrete thing being built + why.
- Lay out **milestones** in `plan.md` (a checklist). The current milestone is the track's
  `next_action`, so RESUME drops you back exactly where the build is.

## The loop
1. **Pick the next milestone** (smallest shippable step toward the project).
2. **Do it with the learner**, teaching just-in-time only what the step needs — prefer
   `worked-examples` (study a solved instance, then they do it) and `deliberate-practice` for a
   sub-skill at the edge; pull in `tutor` only for the conceptual gaps the build exposes.
3. **Capture the traps (this is the point).** When the learner hits a gotcha / bug / wrong mental
   model, record it: a note of what happened, and — with approval — a card from the trap. Mistakes
   made while building are the highest-value review material; route them through `active-recall`.
4. **Close the milestone**: update `plan.md` (done + what was learned), set the next milestone as
   `next_action`, write CONTEXT.md (where the build is, open threads) + a `learning-records/` entry
   for any real insight.
5. **Repeat** to the next milestone; FSRS keeps the captured lessons from fading.

## Composes with
- `worked-examples` + `deliberate-practice` (the doing), `learner-model` (just-in-time depth),
  `active-recall` (turn traps into durable cards), `learning-science` (mission, storage strength).
  Differs from `domain` (source-driven) and `exam` (syllabus + deadline): here the *project* is the
  curriculum.

## Anti-patterns
- Front-loading a course before building — teach just-in-time, let the project pull the need.
- Letting a hard-won gotcha vanish unrecorded — capture it as a note + card.
- Over-teaching theory the milestone doesn't require yet.
