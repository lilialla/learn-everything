# `fsrs_optimize` — personalized FSRS weights (OPT-IN, dependency-heavy)

Fits a **personalized FSRS-6 weight vector** (`w[0..20]`) from your real review
history and writes a data-only `fsrs-weights.json` that the stdlib CORE
scheduler (`scripts/fsrs.py`) can **optionally** load. The built-in FSRS-6
defaults work fine without this; personalized weights are a power-user tune-up.

## What it does

1. Reads `tracks/<id>/review-log.jsonl` — the append-only grade history the
   normal review loop already writes (one JSONL line per graded card).
2. Reconstructs each card's ordered review sequence and reshapes it into the
   [`fsrs-optimizer`](https://github.com/open-spaced-repetition/fsrs-optimizer)
   revlog schema (`card_id`, `review_time`, `review_rating`, `review_state`).
3. Lazily imports `fsrs-optimizer` (which pulls **torch**) and fits the 21
   weights.
4. Writes `fsrs-weights.json` (`{"weights": [...21 floats...], "provenance":
   {...}}`) — per-track or a global one. **Only data is written; `fsrs.py` is
   never modified.**

## Opt-in and dependency-heavy

The fit dependency (`fsrs-optimizer` + `torch` + `pandas`) is **not** part of
the pip-free CORE. It lives only here and is imported **lazily** inside the fit
routine. If it is missing you get a friendly install hint, never a raw
`ImportError`. Importing this package pulls nothing.

```bash
pip install -r adapters/fsrs_optimize/requirements.txt
```

## Gated on real history

Personalized weights **overfit** on small histories, so the adapter **refuses
to fit below ~200 graded reviews** (`--min-reviews`, default `200`) and prints
the count it actually had. You need a few hundred *graded* reviews before
personalized weights mean anything — until then, keep the built-in defaults.

## How it's invoked

```bash
# Global fit across every track -> <repo>/fsrs-weights.json
python3 adapters/fsrs_optimize/optimize.py --track all

# One track -> tracks/<id>/fsrs-weights.json
python3 adapters/fsrs_optimize/optimize.py --track datawhale-llm

# Options
python3 adapters/fsrs_optimize/optimize.py \
    --track all --min-reviews 400 --out /tmp/weights.json --timezone UTC
```

The output `fsrs-weights.json` files are **personal data** and are gitignored
(they live under `tracks/` or the repo root alongside other learner state) —
never commit them.

## Integration note (CORE wiring the maintainer adds — do NOT edit `fsrs.py`)

The adapter only *writes* the weights file. For `scripts/fsrs.py` to *use* it,
add a tiny stdlib loader + precedence walk to `fsrs.py` (no new imports). The
exact hook is in the parent task's integration notes; in short:

```python
# scripts/fsrs.py — add (stdlib only):
def load_weights(path):
    """Load a 21-float weight vector from a fsrs-weights.json, or None."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        w = data["weights"] if isinstance(data, dict) else data
        if isinstance(w, list) and len(w) == 21 and all(
            isinstance(x, (int, float)) for x in w
        ):
            return [float(x) for x in w]
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None  # malformed -> caller falls back to DEFAULT_WEIGHTS, never crash
```

Then in the `schedule` CLI branch, resolve weights by precedence
`--weights <path>` → per-track `tracks/<id>/fsrs-weights.json` → global
`<root>/fsrs-weights.json` → `DEFAULT_WEIGHTS`, and pass the result as
`schedule(..., w=resolved)`. `schedule()` already accepts `w=`, so no formula
changes are needed.

## Tests

`tests/test_fsrs_optimize.py` covers the pure stdlib pieces (log parsing,
revlog reshaping, weights-file round-trip) and **self-skips** the actual fit
when `fsrs-optimizer` is not installed, so core CI stays green with nothing
installed.
