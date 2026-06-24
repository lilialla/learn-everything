#!/usr/bin/env python3
"""URL -> markdown ingestion adapter.

Public surface (the stable contract — keep downstream unchanged):

    ingest_url(url, track, root=None, *, allow_login=False, prefer_local=False,
               today=None) -> {
        "source_md_path": str,   # tracks/<id>/notes/<date>-<slug>-source.md
        "title": str,
        "metadata": {
            "source_url": str, "source_type": str, "fetcher": str,
            "fetched_at": ISO8601-date, "untrusted": True,
            "injection_flagged": bool, "fallback_used": str|None,
            "truncated": bool } }

Raises a typed ``IngestError(reason, source_type, url)`` on bot-check /
paywall / empty / unsupported — never returns a partial file.

Design rules (see plans/specs/2026-06-22-feature-designs.md
"URL -> md Ingestion Adapter"):
  * The genuinely NEW code here is small: classify(), the route dispatcher,
    the frontmatter normalizer, the public->login-gated fallback decision,
    and the IngestError contract.
  * Every fetcher (web scrape, yt-dlp subtitles, mineru OCR, ...) is an
    existing skill/tool wrapped, imported LAZILY with a friendly install hint.
  * Fetched text is UNTRUSTED DATA: wrapped in DATA_BOUNDARY markers and
    scanned for prompt injection; embedded imperatives are never obeyed.
  * The adapter writes EXACTLY one source file. It never touches cards,
    review-state.json, MOC, TRACK.md, or registry.json — those are written
    only by the existing ingest loop, only after human approval.
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

# DATA_BOUNDARY markers — fetched content goes between these and is DATA only.
UNTRUSTED_OPEN = "<<<UNTRUSTED_INPUT>>>"
UNTRUSTED_CLOSE = "<<<END_UNTRUSTED>>>"

# A long source past this many characters is flagged truncated/handoff-worthy
# (Long-Document Ingestion handles chunking; this adapter only flags it).
LARGE_SOURCE_CHARS = 60_000

# Injection red-flag patterns. >=3 hits => treat the whole body as suspicious.
_INJECTION_PHRASES = (
    "ignore previous instructions",
    "ignore all previous",
    "disregard previous",
    "new system prompt",
    "new instructions",
    "from now on",
    "you are now",
    "system:",
    "忽略前面",
    "忽略以上",
    "忽略之前",
    "按我说的做",
)
# Zero-width / direction-override characters that hide injected instructions.
_ZERO_WIDTH = ("​", "‌", "‍", "﻿")
_DIRECTION_OVERRIDE = ("‮", "‭")


class IngestError(Exception):
    """Typed failure for the adapter contract.

    Raised on bot-check / paywall / empty extraction / unsupported type / a
    missing optional dependency. Carries enough context for the skill to
    report the explicit limit. The adapter never writes a partial file before
    raising this.
    """

    def __init__(self, reason: str, source_type: str | None = None,
                 url: str | None = None):
        self.reason = reason
        self.source_type = source_type
        self.url = url
        super().__init__(reason)


# ---------------------------------------------------------------------------
# Pure helpers (stdlib only — unit-testable with nothing installed)
# ---------------------------------------------------------------------------

def classify(url: str) -> str:
    """Map a URL to a source_type: web | wechat | video | pdf | unknown.

    Dispatch is by host + path only; no network. ``unknown`` means the skill
    should ask the user to paste the text manually.
    """
    if not url or not isinstance(url, str):
        return "unknown"
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        return "unknown"
    host = (parsed.netloc or "").lower()
    # Strip a leading "www." for matching; keep credentials/port out.
    if "@" in host:
        host = host.split("@", 1)[1]
    host = host.split(":", 1)[0]
    if host.startswith("www."):
        host = host[4:]
    path = (parsed.path or "").lower()

    # PDF link — by extension on the path (query strings ignored).
    if path.endswith(".pdf"):
        return "pdf"

    # 微信公众号
    if host == "mp.weixin.qq.com":
        return "wechat"

    # Video platforms (B站 / YouTube / 抖音 and their short domains).
    video_hosts = {
        "bilibili.com", "b23.tv",
        "youtube.com", "youtu.be", "m.youtube.com",
        "douyin.com", "iesdouyin.com", "v.douyin.com",
    }
    if host in video_hosts or host.endswith(".bilibili.com") \
            or host.endswith(".youtube.com") or host.endswith(".douyin.com"):
        return "video"

    # Everything else with a real host -> treat as a web article.
    if host:
        return "web"
    return "unknown"


def slugify(text: str, *, max_len: int = 60) -> str:
    """Produce a filesystem-safe slug from a title or URL fragment.

    ASCII-fold what we can, keep CJK characters (titles are often Chinese),
    collapse runs of separators to a single hyphen. Always returns a
    non-empty slug ("untitled" as a last resort) so the filename is valid.
    """
    if not text:
        return "untitled"
    text = unicodedata.normalize("NFKC", str(text)).strip().lower()
    # Drop characters that are unsafe in filenames / path separators, but keep
    # word chars (incl. CJK via \w under re.UNICODE) and spaces/hyphens.
    cleaned_chars = []
    for ch in text:
        if ch.isspace() or ch in "-_":
            cleaned_chars.append("-")
        elif ch.isalnum():
            cleaned_chars.append(ch)
        # else: drop punctuation / emoji / control chars
    slug = "".join(cleaned_chars)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if len(slug) > max_len:
        slug = slug[:max_len].rstrip("-")
    return slug or "untitled"


def scan_injection(text: str) -> dict:
    """Scan fetched body for prompt-injection red flags.

    Returns ``{"flagged": bool, "hits": [str], "count": int}``. >=3 distinct
    red flags => flagged (caller prepends ``[PROMPT_INJECTION_DETECTED]`` and
    keeps the body as DATA only). Stdlib only.
    """
    hits: list[str] = []
    low = (text or "").lower()
    for phrase in _INJECTION_PHRASES:
        if phrase in low:
            hits.append(f"phrase:{phrase}")
    zw_total = sum(text.count(z) for z in _ZERO_WIDTH) if text else 0
    if zw_total >= 5:
        hits.append(f"zero-width:{zw_total}")
    if text and any(d in text for d in _DIRECTION_OVERRIDE):
        hits.append("direction-override")
    return {"flagged": len(hits) >= 3, "hits": hits, "count": len(hits)}


def source_md_path(track: str, slug: str, *, root: Path | None = None,
                   today: str | None = None) -> Path:
    """Resolve the single output path the adapter is allowed to write.

    tracks/<id>/notes/<date>-<slug>-source.md  — matches skills/learn/SKILL.md.
    """
    base = _resolve_root(root)
    day = today or datetime.date.today().isoformat()
    return base / "tracks" / track / "notes" / f"{day}-{slug}-source.md"


def build_source_md(*, body: str, title: str, source_url: str,
                    source_type: str, fetcher: str, fetched_at: str,
                    injection_flagged: bool) -> str:
    """Normalize fetched text into the source `.md`: YAML frontmatter + a
    DATA_BOUNDARY-wrapped body. The body is DATA, never instructions.
    """
    meta_lines = [
        "---",
        f"source_url: {_yaml_scalar(source_url)}",
        f"title: {_yaml_scalar(title)}",
        f"source_type: {source_type}",
        f"fetcher: {fetcher}",
        f"fetched_at: {fetched_at}",
        "untrusted: true",
        f"injection_flagged: {'true' if injection_flagged else 'false'}",
        "---",
    ]
    lead = "[PROMPT_INJECTION_DETECTED]\n\n" if injection_flagged else ""
    return (
        "\n".join(meta_lines)
        + "\n"
        + lead
        + UNTRUSTED_OPEN
        + "\n"
        + (body or "").strip()
        + "\n"
        + UNTRUSTED_CLOSE
        + "\n"
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _resolve_root(root: Path | None) -> Path:
    """Repo root. Prefer the explicit arg; else reuse scripts/registry.py's
    resolver so the adapter and CORE agree on where ``tracks/`` lives.
    """
    if root is not None:
        return Path(root)
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
        import registry  # type: ignore

        return registry.repo_root()
    except Exception:
        # Fallback: repo root is two levels up from adapters/url_ingest/.
        return Path(__file__).resolve().parent.parent.parent


def _yaml_scalar(value: str) -> str:
    """Quote a scalar for single-line frontmatter if it could be misread.

    Mirrors scripts/registry.py:_scalar_to_yaml conservatively; we keep this
    local so the adapter has no import-time CORE dependency.
    """
    text = str(value).replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    if text == "":
        return '""'
    needs_quote = (
        ": " in text
        or text[0] in "#&*!|>%@`\"'[]{},"
        or text.strip() != text
        or text in ("null", "true", "false")
    )
    if needs_quote:
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return text


def _missing_dep(pkg: str, route: str) -> IngestError:
    return IngestError(
        f"the '{route}' route needs the optional package '{pkg}'. "
        f"Install it (e.g. `pip install {pkg}`) or paste the text manually.",
    )


def _empty(text: str) -> bool:
    return len((text or "").strip()) < 40


# ---------------------------------------------------------------------------
# Per-type fetch routes — each wraps an existing tool, imported LAZILY.
# Each returns (body_markdown, title, fetcher_name). They raise IngestError
# (typed) on bot-check / paywall / empty / missing dep — never a raw
# ImportError, never a partial result.
# ---------------------------------------------------------------------------

def _fetch_web(url: str, *, allow_login: bool) -> tuple[str, str, str]:
    """Public-path web article fetch via requests + readability/bs4.

    Login-gated/anti-bot pages are surfaced as IngestError so the skill can
    offer the logged-in-browser path; we never write a half-empty file.
    """
    try:
        import requests  # type: ignore
    except ImportError:
        raise _missing_dep("requests", "web")
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except ImportError:
        raise _missing_dep("beautifulsoup4", "web")

    try:
        resp = requests.get(
            url,
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0 (learn-everything url_ingest)"},
        )
    except Exception as exc:  # network error, DNS, TLS, ...
        raise IngestError(f"network error fetching the page: {exc}", "web", url)

    if resp.status_code in (401, 402, 403, 429):
        raise IngestError(
            f"login/anti-bot wall (HTTP {resp.status_code}); "
            f"try the logged-in-browser path (--allow-login).",
            "web", url,
        )
    if resp.status_code >= 400:
        raise IngestError(f"HTTP {resp.status_code} fetching the page", "web", url)

    html = resp.text or ""
    title = ""
    body = ""
    # Prefer readability-lxml for main-content extraction if available.
    try:
        from readability import Document  # type: ignore

        doc = Document(html)
        title = (doc.short_title() or "").strip()
        content_html = doc.summary(html_partial=True)
    except ImportError:
        content_html = html
    soup = BeautifulSoup(content_html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "aside", "form"]):
        tag.decompose()
    if not title:
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
    body = soup.get_text("\n", strip=True)

    if _empty(body):
        raise IngestError(
            "empty extraction (JS-only page or bot-check); "
            "try the logged-in-browser path or paste the text.",
            "web", url,
        )
    return body, (title or url), "requests+readability"


def _fetch_wechat(url: str, *, allow_login: bool) -> tuple[str, str, str]:
    """微信公众号 (mp.weixin) — wraps the wechat-article-fetch skill
    (Playwright headless). Public articles only.
    """
    try:
        from playwright.sync_api import sync_playwright  # type: ignore  # noqa: F401
    except ImportError:
        raise IngestError(
            "the 'wechat' route wraps the wechat-article-fetch skill, which "
            "needs Playwright (`pip install playwright` + `playwright install "
            "chromium`). Or run the wechat-article-fetch skill manually and "
            "paste the resulting markdown.",
            "wechat", url,
        )
    # Reuse-not-rebuild: defer to the wechat-article-fetch skill rather than
    # re-implementing the Playwright scrape here. Surface it as a known limit
    # until that skill exposes a clean importable entrypoint.
    raise IngestError(
        "wechat fetch is delegated to the wechat-article-fetch skill; run it "
        "on this URL, then paste/point ingest at the produced markdown.",
        "wechat", url,
    )


def _fetch_video(url: str, *, allow_login: bool) -> tuple[str, str, str]:
    """Video subtitles via yt-dlp (wraps the video-notes skill). FunASR audio
    fallback is OUT OF SCOPE here — if no subtitles, fail loudly so the skill
    can route to video-notes/funasr-transcribe.
    """
    try:
        import yt_dlp  # type: ignore
    except ImportError:
        raise _missing_dep("yt-dlp", "video")

    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "quiet": True,
        "no_warnings": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        msg = str(exc).lower()
        if "sign in" in msg or "bot" in msg or "login" in msg or "403" in msg:
            raise IngestError(
                "bot-check / login wall on the video host; YouTube/抖音 often "
                "need a logged-in browser (run video-notes with --browser edge).",
                "video", url,
            )
        raise IngestError(f"failed to read video metadata: {exc}", "video", url)

    title = (info.get("title") or url) if isinstance(info, dict) else url
    subs = {}
    if isinstance(info, dict):
        subs = info.get("subtitles") or info.get("automatic_captions") or {}
    if not subs:
        raise IngestError(
            "no subtitles available for this video. Audio transcription "
            "(FunASR) is out of scope for this adapter — run the video-notes "
            "skill (which falls back to funasr-transcribe) instead.",
            "video", url,
        )
    # We have subtitle tracks but downloading/parsing them is the video-notes
    # skill's job (handles VTT/SRT cleanup + langs). Hand off loudly.
    raise IngestError(
        "subtitles exist but transcript assembly is delegated to the "
        "video-notes skill; run it on this URL and point ingest at the "
        "produced markdown.",
        "video", url,
    )


def _fetch_pdf(url: str, *, allow_login: bool, prefer_local: bool) -> tuple[str, str, str]:
    """PDF link — download then hand off to the doc adapter / mineru-ocr
    (cloud) or case-files-to-md-fast (local, no upload) when prefer_local /
    confidential. PDF OCR is delegated, not rebuilt here.
    """
    try:
        import requests  # type: ignore
    except ImportError:
        raise _missing_dep("requests", "pdf")
    route = "case-files-to-md-fast (local)" if prefer_local else "mineru-ocr"
    raise IngestError(
        f"PDF ingestion is delegated to the doc adapter ({route}). Download "
        f"the PDF and run that skill, then point ingest at the produced "
        f"markdown. (prefer_local={prefer_local})",
        "pdf", url,
    )


_ROUTES = {
    "web": _fetch_web,
    "wechat": _fetch_wechat,
    "video": _fetch_video,
    "pdf": _fetch_pdf,
}


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------

def ingest_url(url: str, track: str, root: Path | None = None, *,
               allow_login: bool = False, prefer_local: bool = False,
               today: str | None = None) -> dict:
    """Fetch ONE url, normalize to a source `.md`, return the adapter contract.

    Writes exactly one file: tracks/<track>/notes/<date>-<slug>-source.md.
    Raises IngestError (typed) on unsupported/bot-check/paywall/empty/missing
    dep — never writes a partial file.
    """
    if not track or not isinstance(track, str):
        raise IngestError("a target track id is required", None, url)

    source_type = classify(url)
    if source_type == "unknown":
        raise IngestError(
            "unsupported URL type — paste the text manually instead.",
            "unknown", url,
        )

    route = _ROUTES[source_type]
    if source_type == "pdf":
        body, title, fetcher = route(url, allow_login=allow_login,
                                     prefer_local=prefer_local)
    else:
        body, title, fetcher = route(url, allow_login=allow_login)

    if _empty(body):
        raise IngestError("empty extraction after fetch", source_type, url)

    scan = scan_injection(body)
    fetched_at = today or datetime.date.today().isoformat()
    truncated = len(body) > LARGE_SOURCE_CHARS

    slug = slugify(title) or slugify(urlparse(url).path) or "source"
    out_path = source_md_path(track, slug, root=root, today=today)
    if not out_path.parent.exists():
        out_path.parent.mkdir(parents=True, exist_ok=True)

    md = build_source_md(
        body=body, title=title, source_url=url, source_type=source_type,
        fetcher=fetcher, fetched_at=fetched_at,
        injection_flagged=scan["flagged"],
    )
    out_path.write_text(md, encoding="utf-8")

    return {
        "source_md_path": str(out_path),
        "title": title,
        "metadata": {
            "source_url": url,
            "source_type": source_type,
            "fetcher": fetcher,
            "fetched_at": fetched_at,
            "untrusted": True,
            "injection_flagged": scan["flagged"],
            "fallback_used": None,
            "truncated": truncated,
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ingest.py",
        description="URL -> markdown source for a learn-everything track.",
    )
    parser.add_argument("--url", required=True, help="the source URL to ingest")
    parser.add_argument("--track", required=True, help="target track id")
    parser.add_argument("--root", default=None,
                        help="repo root (defaults to the auto-detected root)")
    parser.add_argument("--allow-login", action="store_true",
                        help="permit a logged-in-browser path for gated pages")
    parser.add_argument("--prefer-local", action="store_true",
                        help="force local (no-upload) routes for PDFs (confidential)")
    parser.add_argument("--today", default=None,
                        help="override the date stamp (YYYY-MM-DD), for tests")
    args = parser.parse_args(argv)

    try:
        result = ingest_url(
            args.url, args.track,
            root=Path(args.root) if args.root else None,
            allow_login=args.allow_login,
            prefer_local=args.prefer_local,
            today=args.today,
        )
    except IngestError as exc:
        print(f"ingest failed [{exc.source_type or 'unknown'}]: {exc.reason}",
              file=sys.stderr)
        return 1

    md = result["metadata"]
    print(f"wrote {result['source_md_path']}")
    print(f"  title: {result['title']}")
    print(f"  source_type: {md['source_type']}  fetcher: {md['fetcher']}")
    if md["injection_flagged"]:
        print("  WARNING: prompt-injection red flags detected; body kept as DATA only.")
    if md["truncated"]:
        print("  NOTE: large source — consider Long-Document Ingestion (chunked).")
    print("Next: run the learn `ingest` loop on this source .md (human-approved).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
