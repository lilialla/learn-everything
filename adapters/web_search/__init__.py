"""web_search — optional, out-of-CORE web search for the learn skill.

Importing this package pulls in NO third-party dependency (the backend is
resolved lazily only when a search actually runs), so it never touches the
pip-free CORE in scripts/.
"""

from .search import (  # noqa: F401
    WebSearchError,
    format_results_md,
    readiness,
    search,
)
