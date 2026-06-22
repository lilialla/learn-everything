#!/usr/bin/env python3
"""FSRS-6 spaced-repetition scheduler (Python stdlib only).

FSRS-6 (Free Spaced Repetition Scheduler v6) formulas are implemented here
directly from the public FSRS specification. NUMERIC PARITY WITH THE REFERENCE
IMPLEMENTATION (py-fsrs) IS DEFERRED: this module is intended to satisfy the
behavioral invariants the learning OS relies on (deterministic output, grade
ordering of intervals, lapse counting, difficulty clamping, due-date advance).
A future task may port py-fsrs for exact parity.

State machine (intentionally minimal for the MVP): only "new" and "review".
The learning / relearning step ladders of full FSRS are skipped. A brand-new
card has no prior state; the first grade seeds stability/difficulty and moves
the card to "review".

CLI:
    python3 scripts/fsrs.py schedule --state '<json|->' --grade <1|2|3|4> --now YYYY-MM-DD
prints ONE json object: the new card state with keys
    stability, difficulty, due, reps, lapses, last_review, state
"""

import argparse
import json
import math
import sys
from datetime import date, timedelta

# FSRS-6 default weights w[0..20].
DEFAULT_WEIGHTS = [
    0.2172, 1.1771, 3.2602, 16.1507, 7.0114, 0.57, 2.0966, 0.0069, 1.5261,
    0.112, 1.0178, 1.849, 0.1133, 0.3127, 2.2934, 0.2191, 3.0004, 0.7536,
    0.3332, 0.1437, 0.2,
]

REQUESTED_RETENTION = 0.9

# Cap intervals so dates never overflow and reviews stay schedulable.
# 100 years of days is far beyond any practical learning horizon.
MAX_INTERVAL_DAYS = 36500

# DECAY and FACTOR derive from w[20] per the FSRS-6 forgetting curve.
DECAY = -DEFAULT_WEIGHTS[20]
FACTOR = 0.9 ** (1.0 / DECAY) - 1.0


def _clamp(value, low, high):
    """Clamp value into [low, high]."""
    return max(low, min(high, value))


def initial_stability(w, grade):
    """S0 for a brand-new card given its first grade (1..4)."""
    return w[grade - 1]


def initial_difficulty(w, grade):
    """D0(grade): initial difficulty, clamped to [1, 10]."""
    return _clamp(w[4] - math.exp(w[5] * (grade - 1)) + 1.0, 1.0, 10.0)


def retrievability(w, t_days, stability):
    """Probability of recall after t_days given stability S."""
    if stability <= 0:
        return 0.0
    return (1.0 + FACTOR * t_days / stability) ** DECAY


def next_interval(w, stability, retention=REQUESTED_RETENTION):
    """Next interval in whole days for a target retention, minimum 1 day."""
    raw = (stability / FACTOR) * (retention ** (1.0 / DECAY) - 1.0)
    return _clamp(round(raw), 1, MAX_INTERVAL_DAYS)


def next_difficulty(w, difficulty, grade):
    """Difficulty update on review, clamped to [1, 10] (mean reversion)."""
    d_after_grade = difficulty - w[6] * (grade - 3)
    d_reverted = w[7] * initial_difficulty(w, 4) + (1.0 - w[7]) * d_after_grade
    return _clamp(d_reverted, 1.0, 10.0)


def stability_after_success(w, difficulty, stability, retrieval, grade):
    """Stability update for a successful review (grade >= 2)."""
    hard_penalty = w[15] if grade == 2 else 1.0
    easy_bonus = w[16] if grade == 4 else 1.0
    factor = (
        math.exp(w[8])
        * (11.0 - difficulty)
        * (stability ** (-w[9]))
        * (math.exp(w[10] * (1.0 - retrieval)) - 1.0)
        * hard_penalty
        * easy_bonus
    )
    return stability * (1.0 + factor)


def stability_after_lapse(w, difficulty, stability, retrieval):
    """Stability update for a lapse (grade == 1)."""
    return (
        w[11]
        * (difficulty ** (-w[12]))
        * ((stability + 1.0) ** w[13] - 1.0)
        * math.exp(w[14] * (1.0 - retrieval))
    )


def schedule(state, grade, now, w=None, retention=REQUESTED_RETENTION):
    """Compute the new card state.

    state: dict with prior card state, or None for a brand-new card.
    grade: int in {1,2,3,4} (1=Again, 2=Hard, 3=Good, 4=Easy).
    now:   datetime.date of this review.
    Returns a new dict (does not mutate the input).
    """
    if w is None:
        w = DEFAULT_WEIGHTS
    if grade not in (1, 2, 3, 4):
        raise ValueError("grade must be one of 1, 2, 3, 4")

    is_new = not state or state.get("state", "new") == "new" or state.get("stability") is None

    if is_new:
        stability = initial_stability(w, grade)
        difficulty = initial_difficulty(w, grade)
        reps = 1
        lapses = 1 if grade == 1 else 0
    else:
        prior_stability = float(state["stability"])
        prior_difficulty = float(state["difficulty"])
        reps = int(state.get("reps", 0)) + 1
        lapses = int(state.get("lapses", 0))

        # Days elapsed since the last review, used for retrievability.
        last_review = state.get("last_review")
        if last_review:
            elapsed = (now - date.fromisoformat(last_review)).days
        else:
            elapsed = 0
        elapsed = max(0, elapsed)

        retrieval = retrievability(w, elapsed, prior_stability)
        difficulty = next_difficulty(w, prior_difficulty, grade)

        if grade == 1:
            stability = stability_after_lapse(w, difficulty, prior_stability, retrieval)
            lapses += 1
        else:
            stability = stability_after_success(
                w, difficulty, prior_stability, retrieval, grade
            )

    stability = max(0.01, stability)
    interval = next_interval(w, stability, retention)
    due = now + timedelta(days=interval)

    return {
        "stability": stability,
        "difficulty": difficulty,
        "due": due.isoformat(),
        "reps": reps,
        "lapses": lapses,
        "last_review": now.isoformat(),
        "state": "review",
    }


def _parse_state(raw):
    """Parse the --state argument; '-' or empty means a new card."""
    if raw is None or raw == "-" or raw.strip() == "":
        return None
    return json.loads(raw)


def main(argv=None):
    parser = argparse.ArgumentParser(description="FSRS-6 scheduler")
    sub = parser.add_subparsers(dest="command", required=True)

    sched = sub.add_parser("schedule", help="Schedule a card review")
    sched.add_argument("--state", default="-", help="Prior card state JSON, or '-' for new")
    sched.add_argument("--grade", required=True, help="Rating: 1=Again 2=Hard 3=Good 4=Easy")
    sched.add_argument("--now", required=True, help="Review date YYYY-MM-DD")

    args = parser.parse_args(argv)

    if args.command == "schedule":
        try:
            grade = int(args.grade)
        except ValueError:
            print("error: grade must be an integer in {1,2,3,4}", file=sys.stderr)
            return 2
        if grade not in (1, 2, 3, 4):
            print("error: grade must be one of 1, 2, 3, 4", file=sys.stderr)
            return 2
        try:
            now = date.fromisoformat(args.now)
        except ValueError:
            print("error: --now must be a date in YYYY-MM-DD format", file=sys.stderr)
            return 2
        try:
            state = _parse_state(args.state)
        except json.JSONDecodeError as exc:
            print("error: --state is not valid JSON: %s" % exc, file=sys.stderr)
            return 2

        new_state = schedule(state, grade, now)
        print(json.dumps(new_state, ensure_ascii=False))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
