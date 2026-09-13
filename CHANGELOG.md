# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- CI workflow (`.github/workflows/ci.yml`) — Ruff lint + format check + pytest
  on GitHub-hosted `ubuntu-latest` runners (network-free suite).
- OpenSSF Scorecard workflow (`.github/workflows/scorecard.yml`).
- `WORKFLOWS.md` documenting triggers, runners, and required checks.
- `requirements-dev.txt` (ruff, pytest) and `ruff.toml` config.
- README badges (CI, Scorecard, Python, License).
- `make lint` / `make format-check` / `make check` targets.
- Initial POC crawler for batdongsan.com.vn.
- Real-Chrome + CDP Cloudflare bypass (headful, non-automated browser).
- Persistent SQLite queue (`crawl_queue`) with resume-after-crash and dedupe.
- 5-tab worker pool with detail-first claiming.
- Rate limiter: min interval, per-minute cap, exponential backoff.
- Chrome watchdog: auto-relaunch + reconnect on browser death.
- Full listing extraction: 30+ fields, images, videos, agent, JSON-LD timestamps.
- Normalized geography: `cities` / `districts` / `wards` / `streets`.
- Admin-unit compatibility: `location_aliases` + `unresolved_addresses`
  for the 2024–2025 administrative renames.
- `price_history`, `listing_changes`, `raw_snapshots`, FTS5 search.
- Delta mode (`--loop`) re-crawling active listings.
- Rotating file logging, `crawl_runs` tracking, graceful shutdown.
- Unit tests for price/geo parsing (pytest).

### Fixed
- Chrome watchdog stale-connection: invalidate and reconnect when the CDP
  websocket dies instead of failing every request.
- Worker crash-safety: unexpected handler errors mark the item `failed`
  instead of leaving it stuck `in_progress`.
- Reset orphaned `in_progress` rows at startup (resume after crash).
- `wards.district_id` made nullable (wards may be city-direct under the 2025
  two-tier model).
- Queue seeding only runs when the queue is empty (no re-ballooning on restart).
- `categories.transaction` renamed to `txn_type` (SQLite keyword).
- FK ordering: agents inserted before listings.

### Known limitations
- Cloudflare bypass requires **Google Chrome on macOS host**; Linux/container
  Chrome is detected and blocked.
- Phone numbers are masked by the site.
- Street resolution is heuristic (project names may become street rows when an
  address lacks a `Đường` marker).