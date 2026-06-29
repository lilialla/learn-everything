#!/usr/bin/env python3
"""Tests for scripts/security_check.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import security_check  # noqa: E402


class SecurityCheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _init_git(self) -> None:
        subprocess.run(
            ["git", "init"],
            cwd=self.root,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def test_flags_ignored_claudian_token_without_value_output(self):
        cfg = self.root / ".claudian" / "claudian-settings.json"
        cfg.parent.mkdir()
        cfg.write_text(
            '{"sharedEnvironmentVariables":"CLAUDE_CODE_OAUTH_TOKEN=sk-ant-'
            'abcdefghijklmnopqrstuvwxyz123456"}',
            encoding="utf-8",
        )

        findings = security_check.scan_paths([cfg])

        self.assertIn((cfg, "anthropic_token"), findings)
        self.assertIn((cfg, "secret_env_assignment"), findings)
        self.assertNotIn((cfg, "openai_secret_key"), findings)

    def test_empty_or_documented_env_name_is_allowed(self):
        doc = self.root / "README.md"
        doc.write_text(
            "Set CLAUDE_CODE_OAUTH_TOKEN in your local settings.\n"
            "CLAUDE_CODE_OAUTH_TOKEN=\n",
            encoding="utf-8",
        )

        self.assertEqual(security_check.scan_paths([doc]), [])

    def test_candidate_files_adds_known_ignored_runtime_configs(self):
        cfg = self.root / ".claudian" / "claudian-settings.json"
        cfg.parent.mkdir()
        cfg.write_text("{}", encoding="utf-8")

        paths = security_check.candidate_files(self.root)

        self.assertIn(cfg, paths)

    def test_ignore_invariants_are_enforced(self):
        self._init_git()
        (self.root / ".gitignore").write_text(
            "/tracks/*\n"
            "profile.md\n"
            "/registry.json\n"
            ".obsidian/\n"
            ".claudian/\n"
            ".claude/*\n"
            "/fsrs-weights.json\n"
            "providers/*/node_modules/\n",
            encoding="utf-8",
        )

        self.assertEqual(security_check.ignored_path_violations(self.root), [])

    def test_missing_ignore_rule_is_reported(self):
        self._init_git()
        (self.root / ".gitignore").write_text("profile.md\n", encoding="utf-8")

        violations = security_check.ignored_path_violations(self.root)

        self.assertIn(".claudian/claudian-settings.json", violations)

    def test_history_scan_reports_secret_shape_without_value(self):
        self._init_git()
        secret = "sk-proj-" + "a" * 40
        (self.root / "leaked.txt").write_text(secret, encoding="utf-8")
        subprocess.run(["git", "add", "leaked.txt"], cwd=self.root, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Test User",
                "-c",
                "user.email=test@example.com",
                "commit",
                "-m",
                "leak",
            ],
            cwd=self.root,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        (self.root / "leaked.txt").unlink()

        findings = security_check.scan_history(self.root)

        self.assertIn("openai_project_key", [rule for _, rule in findings])
        self.assertFalse(any(secret in location for location, _ in findings))


if __name__ == "__main__":
    unittest.main()
