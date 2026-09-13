# Contributing

Thanks for taking the time to contribute.

## Getting started

- Fork the repository and create a short-lived branch off `develop`.
- Install dependencies: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.
- Run the tests: `.venv/bin/python -m pytest tests/ -q`.

## Conventions

- **Language:** English for commits, issues, and PR text (workspace policy).
- **Commits:** Conventional Commits, imperative subject, capitalized first
  letter (e.g. `fix: Reset stuck crawl_queue rows on startup`).
- **Python:** typed public APIs, Ruff formatting, pytest for behavior.
- No secrets, tokens, or credentials in any diff.

## Code quality gate

Before opening a PR:

1. `git diff --check` (no whitespace errors).
2. `.venv/bin/python -m pytest tests/ -q` (all green).
3. Review the diff for temporary debug artifacts.

## Branch model

Follow the JOOservices branch model: feature/fix branches from `develop`,
PRs into `develop`, full-green CI before merge. This project is currently
marked **POC**, so branch rules may be bypassed until release.

## Commit and PR language

English only — see [AGENTS.md](../../../AGENTS.md).