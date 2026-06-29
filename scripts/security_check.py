#!/usr/bin/env python3
"""Repository secret scanner.

Scans tracked files, unignored new files, and known ignored local runtime
configs that commonly hold tokens. Findings report only file paths + rule
names; secret values are never printed.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MAX_FILE_BYTES = 1_000_000

SKIP_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
}

SENSITIVE_IGNORED_GLOBS = (
    ".claudian/**/*.json",
    ".obsidian/**/*.json",
    ".env",
    ".env.*",
)

REQUIRED_IGNORED_PATHS = (
    "tracks/private-track/TRACK.md",
    "profile.md",
    "registry.json",
    ".obsidian/workspace.json",
    ".claudian/claudian-settings.json",
    ".claude/runtime.json",
    "fsrs-weights.json",
    "providers/wechat-article-fetch/node_modules/package.json",
)


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern[str]


RULES = (
    Rule("anthropic_token", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    Rule("openai_project_key", re.compile(r"sk-proj-[A-Za-z0-9_-]{20,}")),
    Rule(
        "openai_secret_key",
        re.compile(r"(?<![A-Za-z0-9_-])sk-(?!ant-|proj-)[A-Za-z0-9][A-Za-z0-9_-]{32,}"),
    ),
    Rule(
        "secret_env_assignment",
        re.compile(
            r"\b(?:CLAUDE_CODE_OAUTH_TOKEN|OPENAI_API_KEY|ANTHROPIC_API_KEY|"
            r"DATABASE_URL|SUPABASE_SERVICE_ROLE_KEY|GITHUB_TOKEN)\s*=\s*"
            r"(?![\"']?(?:$|#|<|YOUR_|REPLACE_|REDACTED|redacted|placeholder|example))"
            r"[^\"'\s]{8,}",
            re.IGNORECASE,
        ),
    ),
)


def _git_output(
    root: Path,
    args: list[str],
    *,
    text: bool = False,
) -> bytes | str | None:
    cmd = ["git", "-C", str(root), *args]
    try:
        return subprocess.check_output(
            cmd,
            stderr=subprocess.DEVNULL,
            text=text,
        )
    except (OSError, subprocess.CalledProcessError):
        return None


def _git_files(root: Path) -> list[Path]:
    out = _git_output(root, ["ls-files", "--cached", "--others", "--exclude-standard", "-z"])
    if not isinstance(out, bytes):
        return []
    return [root / p.decode("utf-8") for p in out.split(b"\0") if p]


def _fallback_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        files.append(path)
    return files


def candidate_files(root: Path = REPO_ROOT) -> list[Path]:
    seen: set[Path] = set()
    files: list[Path] = []

    base = _git_files(root) or _fallback_files(root)
    for path in base:
        if path.is_file() and path not in seen:
            files.append(path)
            seen.add(path)

    for glob in SENSITIVE_IGNORED_GLOBS:
        for path in root.glob(glob):
            if path.is_file() and path not in seen:
                files.append(path)
                seen.add(path)

    return files


def _read_text(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def scan_paths(paths: list[Path]) -> list[tuple[Path, str]]:
    findings: list[tuple[Path, str]] = []
    for path in paths:
        text = _read_text(path)
        if text is None:
            continue
        for rule in RULES:
            if rule.pattern.search(text):
                findings.append((path, rule.name))
    return findings


def ignored_path_violations(root: Path = REPO_ROOT) -> list[str]:
    """Return private/runtime paths that are no longer ignored by git."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "--stdin"],
            input="\n".join(REQUIRED_IGNORED_PATHS) + "\n",
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return []
    if proc.returncode not in (0, 1):
        return []
    ignored = set(proc.stdout.splitlines())
    return [path for path in REQUIRED_IGNORED_PATHS if path not in ignored]


def _scan_text(location: str, text: str) -> list[tuple[str, str]]:
    return [(location, rule.name) for rule in RULES if rule.pattern.search(text)]


def scan_history(root: Path = REPO_ROOT) -> list[tuple[str, str]]:
    """Scan reachable git history blobs. Reports object/path only, never values."""
    out = _git_output(root, ["rev-list", "--objects", "--all"], text=True)
    if not isinstance(out, str):
        return []

    findings: list[tuple[str, str]] = []
    seen: set[str] = set()
    for line in out.splitlines():
        if not line:
            continue
        parts = line.split(" ", 1)
        oid = parts[0]
        path = parts[1] if len(parts) > 1 else "<unknown>"
        if oid in seen:
            continue
        seen.add(oid)
        size_s = _git_output(root, ["cat-file", "-s", oid], text=True)
        if not isinstance(size_s, str):
            continue
        try:
            size = int(size_s)
        except ValueError:
            continue
        if size > MAX_FILE_BYTES:
            continue
        data = _git_output(root, ["cat-file", "-p", oid])
        if not isinstance(data, bytes):
            continue
        if b"\0" in data:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        findings.extend(_scan_text(f"history:{oid[:12]} {path}", text))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="scan repository files for likely secrets")
    parser.add_argument("--root", default=str(REPO_ROOT), help="repository root to scan")
    parser.add_argument("--history", action="store_true", help="also scan reachable git history")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    findings = scan_paths(candidate_files(root))
    history_findings = scan_history(root) if args.history else []
    ignore_violations = ignored_path_violations(root)
    if findings or history_findings or ignore_violations:
        print("secret check failed: likely secrets found (values redacted)", file=sys.stderr)
        for path, rule in findings:
            try:
                rel = path.resolve().relative_to(root)
            except ValueError:
                rel = path
            print(f"- {rel}: {rule}", file=sys.stderr)
        for location, rule in history_findings:
            print(f"- {location}: {rule}", file=sys.stderr)
        for path in ignore_violations:
            print(f"- {path}: not_ignored_private_runtime_path", file=sys.stderr)
        return 1

    print("secret check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
