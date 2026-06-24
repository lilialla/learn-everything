"""Personalized FSRS-weights optimizer adapter for learn-everything.

Optional, out-of-CORE, dependency-heavy. Reads a track's (or all tracks')
append-only `review-log.jsonl`, fits a personalized FSRS-6 weight vector
(w[0..20]) with `fsrs-optimizer` (which pulls torch), and writes a data-only
`fsrs-weights.json` that the stdlib CORE scheduler (`scripts/fsrs.py`) can
OPTIONALLY load. The adapter NEVER modifies `fsrs.py`; it only writes data.

CORE (scripts/fsrs.py, scripts/registry.py) stays pip-free. The fitting deps
(`fsrs-optimizer`, `torch`, `pandas`) are imported LAZILY inside the fit
routine, with a friendly install hint if absent — importing this package never
pulls a third-party dependency.

The pure pieces (reading review logs, reconstructing per-card review
sequences, building the optimizer revlog rows, writing the weights file) are
stdlib-only so they unit-test with nothing installed. Only the actual weight
fit needs the heavy deps.

Gated on real history: personalized weights are meaningless below a few
hundred graded reviews. The default minimum is 200 (the design notes "needs
>200 graded reviews to mean anything"); below it the adapter refuses and
prints the count it had, rather than writing an overfit vector.
"""

from .optimize import (
    DEFAULT_MIN_REVIEWS,
    OptimizeError,
    WEIGHTS_FILENAME,
    build_revlog_rows,
    read_review_log,
    write_weights,
)

__all__ = [
    "DEFAULT_MIN_REVIEWS",
    "OptimizeError",
    "WEIGHTS_FILENAME",
    "build_revlog_rows",
    "read_review_log",
    "write_weights",
]
