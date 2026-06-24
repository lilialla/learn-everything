# learn-everything MCP server

An [MCP](https://modelcontextprotocol.io) adapter that lets **any MCP-capable host**
(Claude Desktop, Cursor, Cline, etc.) drive the learn-everything learning engine.

It is a **thin host adapter** over the pip-free CORE (`scripts/registry.py`):
every tool calls an existing engine function in-process — no engine logic is
duplicated here, and the CORE is never modified.

## What it exposes

- **Tools** — the engine operations:

  | tool | wraps (`registry.py`) | what it does |
  |---|---|---|
  | `status` | `status_board` | status board across all tracks (due / stale / deadlines) |
  | `plan_day` | `plan_day` | ranked, time-boxed daily plan across active tracks (read-only) |
  | `due` | `due_cards` | list due cards (`due <= today`), one track or all |
  | `grade` | `grade_card` | grade a card 1–4 (FSRS), returns new due date |
  | `add_cards` | `add_cards` | add a batch of human-approved cards (all-or-nothing) |
  | `create_track` | `create_track` | scaffold a new learning track |
  | `ingest_check` | `ingest_check` | pre-flight gate before ingesting content |
  | `session_check` | `session_check` | did the session leave a card / logged reason? |
  | `progress` | `progress` | retention numbers (total / graduated / 7-day accuracy) |
  | `log` | `log_entry` | append a Log row (bumps `last_active` / `next_action`) |
  | `log_question` | `log_question` | record one ad-hoc learner question |
  | `questions` | `questions_stats` | where the learner asked most (ranked) |

- **Prompts** — every `methods/*.md` pedagogy template (`tutor`, `socratic`,
  `feynman`, `active-recall`, …) as an MCP prompt.
- **Resources** — each track under `tracks/<id>/` as `learn://track/<id>` (its
  `TRACK.md`), plus `learn://registry` (the full rebuilt registry).

## Optional dependency

The CORE stays stdlib-only. **This adapter** needs the MCP SDK, imported lazily:

```bash
pip install mcp
```

If it is missing, running the server prints a friendly install message and exits
(no traceback). The tool mapping itself is plain stdlib and works without it —
that is what the smoke test checks.

## Run it

```bash
python3 mcp/server.py        # stdio transport
```

## Register it with a host

Claude Desktop / Cursor MCP config (`claude_desktop_config.json` or the host's
`mcp` settings), using **absolute paths**:

```json
{
  "mcpServers": {
    "learn-everything": {
      "command": "python3",
      "args": ["/ABSOLUTE/PATH/TO/learn everything/mcp/server.py"]
    }
  }
}
```

The server resolves the repo root from its own location, so it reads/writes the
same `tracks/`, `methods/`, and `registry.json` as the `learn` skill and the CLI.

## Data boundary & privacy

- Track resources are **learner data** and may contain **ingested / scraped /
  OCR'd content, which is UNTRUSTED**. Resources are returned as *data* for the
  host to render — never as instructions to follow.
- Resource URIs are validated against path traversal.
- Learner data lives only under `tracks/` (gitignored); this adapter writes
  nothing outside what the CORE functions already write.

## Test

```bash
python3 -m unittest mcp.test_server
```

The mapping tests run with nothing installed; the SDK-wiring test self-skips when
`mcp` is absent, so core CI stays green.
