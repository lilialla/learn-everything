"""Smoke tests for the learn-everything MCP server.

The tool mapping is pure stdlib (it wraps scripts/registry.py in-process), so the
core constructibility tests run with NOTHING installed — keeping core CI green.
The single test that needs the MCP SDK self-skips when it is absent.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SERVER_PATH = Path(__file__).resolve().parent / "server.py"


def _load_server():
    spec = importlib.util.spec_from_file_location("le_mcp_server", _SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _mcp_sdk_present() -> bool:
    # NB: this repo has a local ``mcp/`` directory (where this file lives) that
    # also contains a ``server.py`` — so probing ``mcp`` or ``mcp.server`` finds
    # OUR directory, not the SDK. Probe ``mcp.types``, which only the real SDK
    # provides, with the local dir removed from sys.path during the check.
    import sys

    here = str(Path(__file__).resolve().parent.parent)
    saved = list(sys.path)
    sys.path[:] = [p for p in sys.path if p not in ("", here)]
    cached = sys.modules.pop("mcp", None)
    try:
        return importlib.util.find_spec("mcp.types") is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False
    finally:
        sys.path[:] = saved
        if cached is not None:
            sys.modules["mcp"] = cached


_HAS_MCP = _mcp_sdk_present()

EXPECTED_TOOLS = {
    "status",
    "plan_day",
    "due",
    "grade",
    "add_cards",
    "create_track",
    "ingest_check",
    "session_check",
    "progress",
    "log",
    "log_question",
    "questions",
}


class ToolMappingTests(unittest.TestCase):
    """These run with no pip deps installed (stdlib-only CORE)."""

    def setUp(self) -> None:
        self.server = _load_server()

    def test_tool_mapping_is_constructible(self) -> None:
        specs = self.server.build_tool_specs()
        self.assertEqual(set(specs), EXPECTED_TOOLS)

    def test_every_tool_has_schema_and_handler(self) -> None:
        for name, spec in self.server.build_tool_specs().items():
            self.assertEqual(spec.name, name)
            self.assertEqual(spec.input_schema.get("type"), "object")
            self.assertIn("properties", spec.input_schema)
            self.assertTrue(callable(spec.handler))

    def test_call_tool_rejects_unknown(self) -> None:
        with self.assertRaises(ValueError):
            self.server.call_tool("does-not-exist", {})

    def test_create_track_rejects_path_traversal_id(self) -> None:
        with self.assertRaises(ValueError):
            self.server.call_tool(
                "create_track",
                {
                    "id": "../outside",
                    "title": "Bad",
                    "mode": "domain",
                    "pedagogy": "socratic",
                },
            )

    def test_prompts_enumerate_methods(self) -> None:
        names = {p["name"] for p in self.server.list_method_prompts()}
        # 'tutor' is the orchestration method that always ships.
        self.assertIn("tutor", names)

    def test_resources_include_registry(self) -> None:
        uris = {r["uri"] for r in self.server.list_track_resources()}
        self.assertIn("learn://registry", uris)

    def test_resource_uri_traversal_guarded(self) -> None:
        with self.assertRaises(ValueError):
            self.server.read_track_resource("learn://track/../secret")


@unittest.skipUnless(_HAS_MCP, "MCP SDK not installed (pip install mcp)")
class SdkWiringTests(unittest.TestCase):
    """Only runs when the optional MCP SDK is present."""

    def test_build_server_constructs(self) -> None:
        server = _load_server().build_server()
        self.assertIsNotNone(server)


if __name__ == "__main__":
    unittest.main()
