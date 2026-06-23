---
name: dual-coding
description: >-
  Make an explanation land twice — once in words, once in a complementary picture the model
  draws inline (ASCII / mermaid / a small table), and once concrete beside the abstract. Use
  when a concept is structural, spatial, or relational (a process, a hierarchy, a comparison,
  a flow) and words alone are doing too much work. Carries a short interleaving note for review
  and planning. Composes with tutor (fires during Expose) and active-recall (visuals seed L2
  why/how cards).
---

# dual-coding — say it in words AND a picture

Grounded in Paivio's dual-coding theory and Mayer's multimedia principle: a learner who gets the
same idea through *two* complementary channels — verbal and visual — remembers it better and can
manipulate it more flexibly than one who gets words alone. The catch is **complementary**: the
picture must carry information the words don't, or it's decoration. Pair this with concrete↔abstract
coupling — an abstraction is inert until a concrete instance sits next to it.

**Respond in the user's language.** English here is structural only. Keep visuals' labels bilingual
when the field's canon is English (e.g. 编码器 / encoder).

## When to draw what

Don't draw reflexively — draw when the *shape* of the idea is the hard part. Match the visual to
the structure:

1. **A process / sequence / data flow** → a small **mermaid** `flowchart` or `sequenceDiagram`, or
   an ASCII pipeline (`输入 → 编码 → 注意力 → 输出`). Draw the arrows the words are describing.
2. **A hierarchy / part-whole / decision** → mermaid `graph TD` or an indented ASCII tree. Show
   what contains what.
3. **A comparison along shared dimensions** (two methods, before/after, this-vs-that) → a small
   **markdown table**, one row per option, one column per dimension. Tables are the highest-yield
   visual for "how do these differ."
4. **A quantity, threshold, or trend** → a tiny ASCII axis/sketch or a one-line table of values.
   Just enough to make the relationship visible; don't fake precision.
5. **A spatial/structural object** (a matrix, a stack, a tree of layers) → ASCII boxes laid out in
   the actual geometry, so the layout itself teaches.

If none of these fit — the idea is a plain fact or a feeling — **skip the visual.** A forced diagram
costs attention (split-attention effect) without adding a channel.

## Concrete ↔ abstract pairing (always, even without a diagram)

Never present an abstraction alone. State the general rule, then immediately set one concrete,
fully-worked instance beside it — and say which parts of the instance map to which parts of the
rule. The pairing *is* the teaching; the learner builds the abstraction by seeing it instantiated.

Reach for the abstraction in both directions: give the concrete case first and ask "what's the
general pattern here?", or give the rule first and ask "give me an example that fits." Generating
the missing half is far stickier than reading both.

**CPA note (Concrete–Pictorial–Abstract, Bruner):** for a genuinely new or counter-intuitive idea,
sequence the channels — start with a concrete instance, move to a picture/diagram of it, *then* state
the abstract rule. Don't lead with the symbol when the learner has nothing to hang it on.

## How to run it (inside the tutor loop)

1. During **Expose** (see `methods/tutor.md`): after the plain-words explanation, add the ONE visual
   the structure calls for, then the concrete pair. Words → picture → instance. Don't stack three
   diagrams; one complementary picture beats three pretty ones.
2. Read the learner (see `methods/learner-model.md`): a visual/spatial learner or a `confused` signal
   on a structural concept is the cue to draw earlier and lean on the picture; a `solid` learner may
   only need the table. Let their response, not habit, decide.
3. **Probe through the visual**: ask them to extend it — "add the next node to this flow," "fill the
   empty cell," "where in this diagram does X happen?" Manipulating the picture proves they own the
   structure, not just the words.
4. A clean diagram or comparison table is excellent **L2 (why/how)** card material — the question can
   be "sketch/describe the flow from A to B" or "how do X and Y differ on dimension Z." Propose such
   cards (with approval) through `methods/active-recall.md`'s card-derivation and quality gate — that
   file is the single source for L1/L2/L3 and atomicity; don't re-specify it here.

## Interleaving note (for review & planning)

When **reviewing or planning across sub-topics**, mix related-but-distinct items rather than blocking
all of one topic together. Blocked practice feels easier in the moment but builds weaker retention;
interleaving forces the learner to first *discriminate which idea applies* — and that discrimination
is exactly what transfers to novel problems (Rohrer & Taylor). Concretely: in a review session,
shuffle cards across nearby concepts instead of drilling one concept to exhaustion; when sequencing a
plan, alternate confusable siblings (e.g. precision vs recall) so the learner must tell them apart.
Don't interleave brand-new material the learner can't yet tell apart — introduce each first, then mix.

## Anti-patterns

- **Decorative visuals** — a diagram that just restates the sentence. The picture must add a channel.
- **Drawing everything** — a diagram per sentence buries the one that matters (split-attention).
- **Abstraction with no instance** — stating the rule and moving on; always anchor it concretely.
- **A mismatched visual** — a flowchart for a comparison (use a table), a table for a sequence (use a
  flow). Let the structure pick the form.
- **Interleaving the unlearned** — mixing concepts the learner can't yet distinguish just produces
  noise; teach each, then interleave.
