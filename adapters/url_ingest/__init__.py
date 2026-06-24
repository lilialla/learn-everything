"""URL -> markdown ingestion adapter for learn-everything.

Optional, out-of-CORE. Turns ONE url into a cleaned source `.md` under
`tracks/<id>/notes/<date>-<slug>-source.md`, then the existing `learn`
ingest loop takes over unchanged.

CORE (scripts/fsrs.py, scripts/registry.py) stays pip-free. This adapter's
fetch deps (requests/bs4/readability, yt-dlp, mineru, ...) are imported
LAZILY inside the route that needs them, with a friendly install hint if
absent — importing this package never pulls a third-party dependency.

The pure pieces (classify, slug, frontmatter normalize, injection scan)
are stdlib-only so they unit-test with nothing installed.
"""

from .ingest import (
    IngestError,
    classify,
    ingest_url,
    scan_injection,
    slugify,
)

__all__ = [
    "IngestError",
    "classify",
    "ingest_url",
    "scan_injection",
    "slugify",
]
