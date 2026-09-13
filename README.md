# jooservices/bds-crawler

[![CI](https://github.com/jooservices/bds-crawler/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/jooservices/bds-crawler/actions/workflows/ci.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/jooservices/bds-crawler/badge)](https://securityscorecards.dev/viewer/?uri=github.com/jooservices/bds-crawler)
[![Python Version](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A 24/7 crawler for Vietnam's largest real estate portal
[batdongsan.com.vn](https://batdongsan.com.vn). It bypasses Cloudflare using a
real (non-automated) headful Chrome attached over CDP, extracts full listing
data into a normalized SQLite store, and runs continuously with delta
re-crawls.

- **Language:** Python 3.12+ (Playwright + SQLite)
- **Host constraint:** the Cloudflare bypass currently works **only with
  Google Chrome on a macOS host**. Linux/container Chrome is detected and
  blocked (see [docs/02-concepts/architecture.md](docs/02-concepts/architecture.md)).

## Features

- Real-browser bypass: launches Google Chrome (headful, non-automated) and
  drives it over the Chrome DevTools Protocol (CDP) — Cloudflare passes.
- Persistent SQLite queue (`crawl_queue`) with resume-after-crash and dedupe.
- Worker pool (5 CDP tabs) with detail-first claiming.
- Throttle: minimum interval + per-minute cap + exponential backoff on
  Cloudflare challenges.
- Chrome watchdog: auto-relaunch and reconnect when the browser dies.
- Full upsert: listings, images, videos, agents, `price_history`,
  `listing_changes`, `raw_snapshots`, and FTS5 search.
- Delta mode (`--loop`): re-crawl active listings periodically and track
  price/status changes.
- Normalized Vietnamese geography: cities → districts → wards → streets, plus
  an alias layer for administrative renames (2024–2025 mergers).
- Logging to rotating file + console, `crawl_runs` tracking, graceful shutdown.

## Requirements

- macOS with Google Chrome installed at
  `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
  (override with `BDS_CHROME`).
- Python 3.12+ with a virtual environment.
- `pip install -r requirements.txt` (playwright, curl_cffi, beautifulsoup4).

## Installation

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Quick start

```bash
# fresh database + small crawl (test)
.venv/bin/python -u crawler.py --rebuild --quick --limit 20

# continue from the persistent queue
.venv/bin/python -u crawler.py --limit 100

# run 24/7 (seed full site when queue is empty + delta re-crawl)
.venv/bin/python -u crawler.py --loop
```

## Design notes

- **Primary geography is the site's hierarchy** (batdongsan still uses the old
  district/ward names). Official 2025 units are normalized via
  `location_aliases`, never as the primary key.
- `cf_clearance` is bound to the browser TLS fingerprint; do **not** attempt
  HTTP-level scraping with the cookie (curl_cffi is kept for experimentation,
  not the working path).
- Phone numbers on the site are masked (`0906 233 ***`) — the crawler stores
  them as displayed.

## Documentation

- [Getting started](docs/01-getting-started/installation.md)
- [Architecture](docs/02-concepts/architecture.md)
- [Crawler CLI & 24/7 operations](docs/03-operations/crawler-cli.md)
- [Data model](docs/03-operations/data-model.md)
- [Admin-unit compatibility](docs/03-operations/admin-compatibility.md)
- [Audit report](docs/03-operations/audit.md)
- [Workflows](WORKFLOWS.md)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)

## Development

```bash
.venv/bin/python -m pytest tests/ -q              # unit tests (parser + geo resolver)
.venv/bin/ruff check .                            # lint
.venv/bin/ruff format --check .                   # format check
.venv/bin/python -u crawler.py --rebuild --quick --limit 20   # smoke crawl
```

## Community

- [Contributing guide](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

## License

MIT — see [LICENSE](LICENSE).