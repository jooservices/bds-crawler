# jooservices/bds-crawler

This file adds project-only rules.

- Python 3.12+ (Playwright + SQLite); see `README.md` and `docs/`.
- Cloudflare bypass requires Google Chrome on a **macOS host** (Linux/container
  Chrome is detected and blocked).
- CI on GitHub-hosted `ubuntu-latest` runners (ruff + pytest, network-free).
- Branch model: `master` + `develop`, PR required, full-green CI.

Workspace policy lives at the JOOservices workspace root; this file must not
restate or weaken it.