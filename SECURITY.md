# Security & privacy

## Reporting a vulnerability

Please **do not** open a public issue for a security problem. Use GitHub's private
**"Report a vulnerability"** button under the repository's **Security** tab to open a private
advisory. Include steps to reproduce and the impact. You'll get a response as soon as possible.

## Data-handling model (what you should know as a user)

learn-everything is local-first and privacy-conscious by design:

- **Your learning data stays on your machine.** Everything under `tracks/` (notes, cards, the
  memory digest, question logs) plus `profile.md`, `registry.json`, `.obsidian/`, and `.claudian/`
  are **gitignored** and never committed.
- **Source text is sent to the host model.** When you ask the tutor to learn a source, that text
  goes to the host model (e.g. Claude). Do **not** ingest material you aren't authorized to send to
  a third-party model — confirm first for privileged, client, or otherwise confidential documents.
- **Untrusted input is treated as data, not instructions.** Imperative phrasing embedded in a
  document or web page (including hidden/zero-width text) is flagged, never obeyed.
- **Don't commit secrets.** The Claudian auth token lives in its plugin settings (gitignored);
  never paste tokens or credentials into tracked files.

## Local secret check

Before committing, run:

```bash
python3 scripts/security_check.py --history
```

The check scans tracked files, unignored new files, known ignored local runtime configs such as
`.claudian/` and `.obsidian/`, the required privacy-ignore invariants, and (with `--history`)
reachable git history. It reports only file paths and rule names; secret values are never printed.
If it flags a real token, rotate that token, remove it from local files/history, then rerun the check.

## Scope

This is alpha software with no warranty (MIT). The engine is offline and dependency-free; the
network surface is whatever your host model / Obsidian plugins introduce — review their security
posture too.
