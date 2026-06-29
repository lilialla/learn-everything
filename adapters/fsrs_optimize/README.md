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

## Integration note

The adapter only *writes* the weights file. The stdlib core already knows how
to read it:

- `scripts/fsrs.py load_weights(path)` accepts either `{"weights": [...]}` or a
  raw 21-number list and falls back safely on missing or malformed files.
- `scripts/fsrs.py schedule --weights <path>` passes loaded weights into the
  scheduler.
- `scripts/registry.py` automatically passes a per-track
  `tracks/<id>/fsrs-weights.json` when present.

Malformed or missing weights never crash scheduling; the built-in defaults are
used instead.

## Tests

`tests/test_fsrs_optimize.py` covers the pure stdlib pieces (log parsing,
revlog reshaping, weights-file round-trip) and **self-skips** the actual fit
when `fsrs-optimizer` is not installed, so core CI stays green with nothing
installed.
