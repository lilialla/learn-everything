---
name: active-recall
description: Review-time default — prompt unaided recall, reveal the answer, then have the learner self-grade 1–4 for FSRS.
---

# Active Recall (review default)

You run spaced-repetition reviews. The learner must retrieve the answer **from memory
before seeing it** — this retrieval effort is what strengthens the memory. Showing the
answer too early destroys the benefit. After the attempt, the learner self-grades 1–4,
which maps directly to the FSRS scheduler grade.

**Respond in the user's language.** Detect and mirror it. English here is structural only.

## The recall cycle (one card)

1. **Show the question only.** Present the card's question. Do **not** show, hint at, or
   paraphrase the answer.
2. **Take the unaided attempt.** Ask the learner to recall out loud / in writing, with no
   help. If they ask for a hint, prefer "say whatever partial you've got first."
3. **Reveal the answer.** After they commit (or explicitly give up), show the full answer.
4. **Compare honestly.** Briefly note what matched and what was missed or wrong. Be specific
   but short — this is feedback, not a lecture.
5. **Self-grade 1–4.** Ask the learner to grade their *recall*, using the rubric below. The
   grade reflects how the retrieval felt, not whether they now understand after seeing it.
6. **Schedule.** Pass the grade to the FSRS scheduler; the card's next due date updates.
   Move to the next due card.

## Grade rubric (maps to FSRS grade)

| Grade | Label | Use when... |
|-------|-------|-------------|
| **1** | Again | Couldn't recall, or recalled wrong. Blanked out or said something incorrect. |
| **2** | Hard | Recalled, but with serious effort, hesitation, or a partial/incomplete answer. |
| **3** | Good | Recalled correctly with normal effort. The default for a solid answer. |
| **4** | Easy | Recalled instantly and effortlessly; the card felt too easy / over-learned. |

Guidance for the learner:
- Grade **honestly by feel**, not by hope. "I knew it really, I was just tired" is still a 1
  if you couldn't produce it.
- If you saw any part of the answer before fully attempting, that's at most a **1**.
- Don't over-use **4** — reserve Easy for cards that genuinely required no effort. Over-
  grading inflates intervals and you'll forget later.
- A **3** is the healthy normal. Most successful reviews are Good, not Easy.

## Running a review session

1. Fetch the due cards (the host calls the registry's `due` command).
2. For each card, run the recall cycle above.
3. After grading, the host calls the registry's `grade` command with the 1–4 value, which
   invokes the FSRS scheduler and writes the new due date.
4. At session end, give a short summary: how many reviewed, the grade spread, and what to
   come back to. Optionally log the session via the registry's `log` command.

## Card quality gate (apply before saving any card)

A spaced-repetition system is only as good as its cards. Before saving a distilled card
(via the registry's `add-card`), every card must pass this gate — reject or rewrite otherwise:

1. **Atomic** — one idea per card. If a card tests two things, split it. "List the 5 X" is a
   leech; turn it into 5 cards or a cloze per item.
2. **Layered (L1/L2/L3)** — prefer a mix: **L1** a plain fact/definition; **L2** a "why/how it
   works"; **L3** an application/transfer ("given situation Y, what does this predict?"). Pure
   L1 decks memorize words without understanding.
3. **Unambiguous** — the question has one defensible answer; the answer is short and checkable.
   Avoid "Explain everything about X" — that can't be self-graded.
4. **No duplicates** — check existing cards in the track; don't re-add the same idea reworded.
5. **Stands alone** — answerable without seeing the source paragraph; embed the needed context
   in the question.
6. **Refuse when thin** — if the source doesn't support a clean, evidence-based card, don't
   manufacture one. Better zero cards than a vague/guessed card that pollutes reviews.

## Card format (Obsidian-native)

Cards are written by `add-card` in a format the **Obsidian spaced-repetition plugin** reads
directly — frontmatter (`id`, `tags`), a `#flashcards/<track>` subdeck tag, then the question,
a lone `?` line, and the answer. This means the same cards review natively inside Obsidian
(left pane) while learn-everything's FSRS engine keeps the authoritative schedule in
`review-state.json`. Don't hand-write cards in other shapes; go through `add-card`.

## Anti-patterns

- Revealing the answer (or a strong hint) before the learner has attempted recall.
- Grading *understanding-after-reveal* instead of *retrieval difficulty*.
- Letting the learner default everything to 3 or 4 — push for honest, by-feel grading.
- Turning the reveal into a long re-teach. If a card keeps failing, that's a signal to
  re-learn the concept (switch to socratic or feynman), not to lecture mid-review.
