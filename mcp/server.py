#!/usr/bin/env python3
"""learn-everything MCP server.

Wraps the pip-free learn-everything CORE (``scripts/registry.py``) so any
MCP-capable host (Claude Desktop, Cursor, etc.) can drive the learning engine.

Design / invariants
--------------------
- The CORE stays pip-free: this server imports ``scripts.registry`` directly and
  calls its functions IN-PROCESS. No subprocess, no reimplementation of engine
  logic — every tool is a thin wrapper.
- The MCP SDK (``mcp`` / ``fastmcp``) is the ONLY dependency and is imported
  LAZILY inside ``build_server()`` / ``main()``. Importing this module (e.g. the
  smoke test) never requires the SDK. If it is missing, the user gets a friendly
  ``pip install mcp`` message, never a raw ImportError.
- The tool mapping (``TOOL_SPECS`` + ``call_tool``) is plain stdlib data, so it
  is constructible and testable with nothing installed.

Exposed surfaces
----------------
- TOOLS    — engine ops: status, plan_day, due, grade, add_cards, create_track,
             ingest_check, session_check, progress, log, log_question, questions.
- PROMPTS  — every ``methods/*.md`` (pedagogy templates) as an MCP prompt.
- RESOURCES— every track under ``tracks/<id>/`` (its ``TRACK.md``) as a resource,
             plus a ``learn://registry`` overview resource.

Run:    python3 mcp/server.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

# --- locate and import the CORE (stdlib only) -------------------------------
# mcp/server.py -> repo root is the parent dir.
_MCP_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _MCP_DIR.parent
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import registry  # noqa: E402  (stdlib-only CORE; intentional late path setup)

METHODS_DIR = _REPO_ROOT / "methods"
TRACKS_DIR = _REPO_ROOT / "tracks"

SDK_MISSING_MSG = (
    "The MCP SDK is not installed. Install it with:\n\n"
    "    pip install mcp\n\n"
    "The learn-everything CORE itself stays pip-free; only this host adapter "
    "needs the 'mcp' package."
)


# ---------------------------------------------------------------------------
# Tool specs: a pure-data mapping. Each entry is a thin wrapper over a CORE
# function in scripts/registry.py. No SDK needed to build or call these, which
# keeps the mapping testable with nothing installed.
#
# Each handler takes a single dict of arguments and returns a JSON-able result.
# ---------------------------------------------------------------------------


def _opt(args: dict, key: str, default: Any = None) -> Any:
    """Return args[key] if present and not None, else the default."""
    val = args.get(key, default)
    return default if val is None else val


def _tool_status(args: dict) -> Any:
    return registry.status_board(_opt(args, "today"))


def _tool_plan_day(args: dict) -> Any:
    return registry.plan_day(
        _opt(args, "today"),
        _opt(args, "minutes"),
        _opt(args, "energy", "normal"),
    )


def _tool_due(args: dict) -> Any:
    return registry.due_cards(_opt(args, "track", "all"), _opt(args, "today"))


def _tool_grade(args: dict) -> Any:
    new_due = registry.grade_card(
        args["track"],
        args["card"],
        int(args["grade"]),
        today=_opt(args, "today"),
    )
    return {"track": args["track"], "card": args["card"], "new_due": new_due}


def _tool_add_cards(args: dict) -> Any:
    cards = args["cards"]
    if isinstance(cards, str):
        cards = json.loads(cards)
    new_ids = registry.add_cards(args["track"], cards, today=_opt(args, "today"))
    return {"track": args["track"], "added": new_ids}


def _tool_create_track(args: dict) -> Any:
    path = registry.create_track(
        args["id"],
        args["title"],
        args["mode"],
        args["pedagogy"],
        deadline=_opt(args, "deadline"),
        goal=_opt(args, "goal", ""),
    )
    return {"id": args["id"], "path": str(path)}


def _tool_ingest_check(args: dict) -> Any:
    return registry.ingest_check(args["track"])


def _tool_session_check(args: dict) -> Any:
    return registry.session_check(args["track"])


def _tool_progress(args: dict) -> Any:
    return registry.progress(_opt(args, "track", "all"), _opt(args, "today"))


def _tool_log(args: dict) -> Any:
    registry.log_entry(
        args["track"],
        args["what"],
        next_action=_opt(args, "next_action"),
        artifacts=_opt(args, "artifacts", ""),
        no_cards_reason=_opt(args, "no_cards_reason"),
    )
    return {"track": args["track"], "logged": True}


def _tool_log_question(args: dict) -> Any:
    return registry.log_question(
        args["track"],
        args["concept"],
        args["question"],
        term=_opt(args, "term"),
        today=_opt(args, "today"),
    )


def _tool_questions(args: dict) -> Any:
    return registry.questions_stats(_opt(args, "track", "all"), _opt(args, "today"))


class ToolSpec:
    """A single MCP tool: name, description, JSON-schema, and a handler."""

    __slots__ = ("name", "description", "input_schema", "handler")

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: dict,
        handler: Callable[[dict], Any],
    ) -> None:
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.handler = handler


def _schema(properties: dict, required: list[str] | None = None) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


_STR = {"type": "string"}
_INT = {"type": "integer"}


def build_tool_specs() -> dict[str, ToolSpec]:
    """Construct the full tool mapping. Pure stdlib — no SDK required.

    This is what the smoke test asserts is constructible with nothing installed.
    """
    specs = [
        ToolSpec(
            "status",
            "Status board across all tracks (due counts, stale, deadlines).",
            _schema({"today": _STR}),
            _tool_status,
        ),
        ToolSpec(
            "plan_day",
            "Ranked, time-boxed daily plan across active tracks (read-only).",
            _schema(
                {
                    "today": _STR,
                    "minutes": _INT,
                    "energy": {"type": "string", "enum": ["low", "normal", "high"]},
                }
            ),
            _tool_plan_day,
        ),
        ToolSpec(
            "due",
            "List due cards (due <= today), one track or all.",
            _schema({"track": _STR, "today": _STR}),
            _tool_due,
        ),
        ToolSpec(
            "grade",
            "Grade a card (FSRS). grade is 1-4 (again/hard/good/easy). "
            "Returns the new due date.",
            _schema(
                {"track": _STR, "card": _STR, "grade": _INT, "today": _STR},
                required=["track", "card", "grade"],
            ),
            _tool_grade,
        ),
        ToolSpec(
            "add_cards",
            "Add a batch of human-approved cards (all-or-nothing). `cards` is a "
            "list of {question, answer, tags?}.",
            _schema(
                {
                    "track": _STR,
                    "cards": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "question": _STR,
                                "answer": _STR,
                                "tags": {"type": "array", "items": _STR},
                            },
                            "required": ["question", "answer"],
                        },
                    },
                    "today": _STR,
                },
                required=["track", "cards"],
            ),
            _tool_add_cards,
        ),
        ToolSpec(
            "create_track",
            "Scaffold a new learning track (TRACK.md + skeleton files).",
            _schema(
                {
                    "id": _STR,
                    "title": _STR,
                    "mode": _STR,
                    "pedagogy": _STR,
                    "deadline": _STR,
                    "goal": _STR,
                },
                required=["id", "title", "mode", "pedagogy"],
            ),
            _tool_create_track,
        ),
        ToolSpec(
            "ingest_check",
            "Pre-flight gate before ingesting content (track ready? MISSION filled?).",
            _schema({"track": _STR}, required=["track"]),
            _tool_ingest_check,
        ),
        ToolSpec(
            "session_check",
            "Did this session leave a card or a logged no-card reason?",
            _schema({"track": _STR}, required=["track"]),
            _tool_session_check,
        ),
        ToolSpec(
            "progress",
            "Retention numbers per track (total / graduated / 7-day accuracy).",
            _schema({"track": _STR, "today": _STR}),
            _tool_progress,
        ),
        ToolSpec(
            "log",
            "Append a Log row to a track (bumps last_active / next_action).",
            _schema(
                {
                    "track": _STR,
                    "what": _STR,
                    "next_action": _STR,
                    "artifacts": _STR,
                    "no_cards_reason": _STR,
                },
                required=["track", "what"],
            ),
            _tool_log,
        ),
        ToolSpec(
            "log_question",
            "Record one ad-hoc learner question (quantitative question tracking).",
            _schema(
                {
                    "track": _STR,
                    "concept": _STR,
                    "question": _STR,
                    "term": _STR,
                    "today": _STR,
                },
                required=["track", "concept", "question"],
            ),
            _tool_log_question,
        ),
        ToolSpec(
            "questions",
            "Where the learner asked most — per-concept counts, ranked.",
            _schema({"track": _STR, "today": _STR}),
            _tool_questions,
        ),
    ]
    return {spec.name: spec for spec in specs}


def call_tool(name: str, arguments: dict | None) -> Any:
    """Dispatch a tool call to its CORE wrapper. Stdlib-only, SDK-free."""
    specs = build_tool_specs()
    if name not in specs:
        raise ValueError(f"unknown tool '{name}'")
    return specs[name].handler(arguments or {})


# ---------------------------------------------------------------------------
# Prompts: methods/*.md (pedagogy templates) exposed as MCP prompts.
# Resources: tracks/<id>/TRACK.md exposed as MCP resources, plus the registry.
# Both are pure-data discovery; no SDK needed to enumerate them.
# ---------------------------------------------------------------------------


def list_method_prompts() -> list[dict]:
    """Enumerate methods/*.md as prompt specs {name, description, path}."""
    if not METHODS_DIR.is_dir():
        return []
    out = []
    for md in sorted(METHODS_DIR.glob("*.md")):
        name = md.stem
        out.append(
            {
                "name": name,
                "description": f"learn-everything pedagogy method: {name}",
                "path": str(md),
            }
        )
    return out


def read_method_prompt(name: str) -> str:
    """Return the markdown body of a method prompt. Treated as TRUSTED template
    text shipped in the repo — but still rendered as a prompt, never executed."""
    path = METHODS_DIR / f"{name}.md"
    if not path.is_file():
        raise ValueError(f"unknown method prompt '{name}'")
    return path.read_text(encoding="utf-8")


def list_track_resources() -> list[dict]:
    """Enumerate tracks as resources {uri, name, path}. learn://track/<id>."""
    out = [
        {
            "uri": "learn://registry",
            "name": "registry",
            "description": "All tracks overview (rebuilt from TRACK.md files).",
            "path": None,
        }
    ]
    if not TRACKS_DIR.is_dir():
        return out
    for tdir in sorted(p for p in TRACKS_DIR.iterdir() if p.is_dir()):
        track_md = tdir / "TRACK.md"
        if not track_md.is_file():
            continue
        out.append(
            {
                "uri": f"learn://track/{tdir.name}",
                "name": tdir.name,
                "description": f"Track {tdir.name} (TRACK.md frontmatter + body).",
                "path": str(track_md),
            }
        )
    return out


def read_track_resource(uri: str) -> str:
    """Return resource contents for a learn:// URI.

    NOTE: track content is LEARNER DATA / may include ingested (UNTRUSTED) text;
    it is returned as data for the host to render, never as instructions.
    """
    if uri == "learn://registry":
        return json.dumps(registry.rebuild_registry(), ensure_ascii=False, indent=2)
    prefix = "learn://track/"
    if uri.startswith(prefix):
        track_id = uri[len(prefix):]
        # Guard against path traversal in the resource id.
        if "/" in track_id or ".." in track_id or not track_id:
            raise ValueError(f"invalid track resource uri '{uri}'")
        path = TRACKS_DIR / track_id / "TRACK.md"
        if not path.is_file():
            raise ValueError(f"unknown track resource '{uri}'")
        return path.read_text(encoding="utf-8")
    raise ValueError(f"unknown resource uri '{uri}'")


# ---------------------------------------------------------------------------
# SDK wiring (lazy). Everything above works without the MCP SDK installed.
# ---------------------------------------------------------------------------


def _import_sdk():
    """Lazy-import the low-level MCP SDK with a friendly install message.

    The low-level ``mcp.server.Server`` lets us pass our rich JSON schemas
    (``ToolSpec.input_schema``) verbatim, instead of having a high-level
    framework re-derive them from function signatures — keeping the schema in
    ``build_tool_specs()`` the single source of truth.
    """
    # This repo has its own ``mcp/`` directory (where this file lives). On
    # sys.path it can shadow the installed ``mcp`` SDK as a namespace package.
    # Drop path entries that contain our local ``mcp/`` for the duration of the
    # import so the real site-packages SDK resolves.
    here = _REPO_ROOT
    saved = list(sys.path)
    sys.path[:] = [
        p
        for p in sys.path
        if p not in ("", str(here)) and (Path(p) / "mcp").resolve() != _MCP_DIR
    ]
    # Evict any namespace-package shim already cached for our local dir.
    cached = sys.modules.pop("mcp", None)
    try:
        import mcp.types as types  # type: ignore
        from mcp.server import Server  # type: ignore
        from mcp.server.stdio import stdio_server  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only without SDK
        if cached is not None:
            sys.modules["mcp"] = cached
        raise SystemExit(SDK_MISSING_MSG) from exc
    finally:
        sys.path[:] = saved
    return types, Server, stdio_server


def build_server():
    """Construct the low-level MCP Server with tools/prompts/resources wired.

    Requires the MCP SDK. Raises SystemExit with a friendly message if missing.
    Tools wrap the CORE; prompts are ``methods/*.md``; resources are tracks.
    """
    types, Server, _ = _import_sdk()
    specs = build_tool_specs()
    server = Server("learn-everything")

    @server.list_tools()
    async def _list_tools():
        return [
            types.Tool(
                name=spec.name,
                description=spec.description,
                inputSchema=spec.input_schema,
            )
            for spec in specs.values()
        ]

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict | None):
        result = call_tool(name, arguments)
        text = json.dumps(result, ensure_ascii=False, indent=2)
        return [types.TextContent(type="text", text=text)]

    @server.list_prompts()
    async def _list_prompts():
        return [
            types.Prompt(name=p["name"], description=p["description"])
            for p in list_method_prompts()
        ]

    @server.get_prompt()
    async def _get_prompt(name: str, arguments: dict | None = None):
        body = read_method_prompt(name)
        return types.GetPromptResult(
            description=f"learn-everything method: {name}",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(type="text", text=body),
                )
            ],
        )

    @server.list_resources()
    async def _list_resources():
        return [
            types.Resource(
                uri=r["uri"], name=r["name"], description=r["description"]
            )
            for r in list_track_resources()
        ]

    @server.read_resource()
    async def _read_resource(uri):
        return read_track_resource(str(uri))

    return server


async def _serve() -> None:  # pragma: no cover - requires SDK + event loop
    types, _, stdio_server = _import_sdk()
    server = build_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main(argv: list[str] | None = None) -> int:
    import asyncio

    asyncio.run(_serve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
