# Workflows

GitHub Actions for `jooservices/bds-crawler`. All jobs use GitHub-hosted
`ubuntu-latest` runners.

> The crawler's Cloudflare bypass requires Google Chrome on a **macOS host**;
> CI deliberately runs only the network-free unit test suite (no Chrome, no
> site access).

## CI

- **File:** `.github/workflows/ci.yml`
- **Triggers:** `pull_request` to `master`/`develop`; `push` to `develop`.
- **Jobs:**
  - `lint` — `ruff check .` + `ruff format --check .`
  - `test` — `pytest -q tests/`
- **Runner:** `ubuntu-latest`
- **Required check (develop/master):** `CI`

## OpenSSF Scorecard

- **File:** `.github/workflows/scorecard.yml`
- **Triggers:** `push` to `develop`; weekly schedule (Monday 00:00 UTC);
  manual `workflow_dispatch`.
- **Runner:** `ubuntu-latest` (required for `publish_results`).
- Publishes SARIF results to the repository's security dashboard.

## Branch protection

`master` and `develop` require:

- Pull requests (no direct push).
- The **CI** status check to pass.