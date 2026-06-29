# Adapters

Optional adapters connect the pip-free learning core in `scripts/` to external
inputs and heavier dependencies. They may import optional packages lazily, but
the core must never import adapter code.

## Entry Points

- `url_ingest/ingest.py` turns one URL into a gitignored source note.
- `doc_ingest/ingest_doc.py` extracts a local document and hands structured text
  to `scripts/structure.py`.
- `web_search/search.py` returns untrusted search results for verification.
- `fsrs_optimize/optimize.py` fits optional personalized FSRS weights.
- `safety.py` owns shared untrusted-data markers and prompt-injection scanning
  for ingestion/search adapters.

## Maintenance Rules

- Preserve adapter public functions; callers and tests should not need to know
  which optional dependency backed a route.
- Keep fetched or extracted text between `UNTRUSTED_INPUT` markers and treat it
  as data only.
- Add new prompt-injection indicators in `safety.py`, not in individual
  adapters.
- Do not write learner data outside `tracks/<id>/` unless the command is an
  explicit tooling or test action.

## Verification

Run the full dependency-free suite before changing adapter contracts:

```bash
python3 -m unittest discover -v
python3 -m unittest mcp.test_server -v
python3 scripts/security_check.py --history
```
