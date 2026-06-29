"""Shared safety helpers for optional ingestion/search adapters.

The CORE under ``scripts/`` stays independent of this package. Adapter paths
that ingest external text all use this module so the untrusted-data boundary
and prompt-injection rules do not drift apart.
"""

from __future__ import annotations

UNTRUSTED_OPEN = "<<<UNTRUSTED_INPUT>>>"
UNTRUSTED_CLOSE = "<<<END_UNTRUSTED>>>"
PROMPT_INJECTION_MARKER = "[PROMPT_INJECTION_DETECTED]"
ESCAPED_UNTRUSTED_OPEN = "<<<UNTRUSTED_INPUT_ESCAPED>>>"
ESCAPED_UNTRUSTED_CLOSE = "<<<END_UNTRUSTED_ESCAPED>>>"

INJECTION_PHRASES = (
    "ignore previous instructions",
    "ignore all previous",
    "disregard previous",
    "disregard the above",
    "new system prompt",
    "new instructions",
    "from now on",
    "you are now",
    "system:",
    "忽略前面",
    "忽略以上",
    "忽略之前",
    "按我说的做",
    "新的系统提示",
)

ZERO_WIDTH_CHARS = ("​", "‌", "‍", "﻿")
DIRECTION_OVERRIDE_CHARS = ("‮", "‭")


def scan_prompt_injection(text: str, *, threshold: int = 3) -> dict:
    """Return prompt-injection indicators for untrusted text.

    ``flagged`` is true when at least ``threshold`` distinct indicators are
    present. The result is data-only: callers may log/report ``hits`` but must
    never treat untrusted text as instructions.
    """
    text = text or ""
    low = text.lower()
    hits: list[str] = []
    for phrase in INJECTION_PHRASES:
        if phrase in low:
            hits.append(f"phrase:{phrase}")
    zero_width_total = sum(text.count(ch) for ch in ZERO_WIDTH_CHARS)
    if zero_width_total >= 5:
        hits.append(f"zero-width:{zero_width_total}")
    if any(ch in text for ch in DIRECTION_OVERRIDE_CHARS):
        hits.append("direction-override")
    return {"flagged": len(hits) >= threshold, "hits": hits, "count": len(hits)}


def wrap_untrusted_text(
    text: str,
    *,
    include_flag_details: bool = False,
) -> tuple[str, list[str]]:
    """Wrap text in DATA_BOUNDARY markers and return ``(wrapped, hits)``."""
    scan = scan_prompt_injection(text)
    header = ""
    if scan["flagged"]:
        details = ""
        if include_flag_details and scan["hits"]:
            details = " " + "; ".join(scan["hits"])
        header = f"{PROMPT_INJECTION_MARKER}{details}\n\n"
    body = f"{UNTRUSTED_OPEN}\n{escape_untrusted_markers(text)}\n{UNTRUSTED_CLOSE}\n"
    return header + body, list(scan["hits"])


def escape_untrusted_markers(text: str) -> str:
    """Neutralize DATA_BOUNDARY sentinels that appear inside untrusted text."""
    return (
        (text or "")
        .replace(UNTRUSTED_OPEN, ESCAPED_UNTRUSTED_OPEN)
        .replace(UNTRUSTED_CLOSE, ESCAPED_UNTRUSTED_CLOSE)
    )
