<!-- Thanks for contributing! Keep PRs focused. -->

## What & why

<!-- What does this change, and why? Link any issue: Fixes #123 -->

## Type

- [ ] feat
- [ ] fix
- [ ] docs
- [ ] refactor / test / chore

## Checklist

- [ ] `python3 -m unittest discover -v` passes
- [ ] `python3 -m unittest mcp.test_server -v` passes
- [ ] `python3 scripts/security_check.py --history` passes
- [ ] No personal/learner data or secrets in the diff
- [ ] Invariants hold (pip-free stdlib core · markdown = source of truth · cards Obsidian-SR
      compatible · teach-first · nothing persisted without approval · DATA_BOUNDARY · privacy)
- [ ] If behavior changed, a test asserts it
- [ ] Optional adapters stay out-of-core, lazy-dependency, and covered by focused tests
