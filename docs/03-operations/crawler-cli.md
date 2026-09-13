# Crawler CLI & 24/7 operations

## Command-line options

```
usage: crawler.py [-h] [--rebuild] [--quick] [--limit LIMIT] [--loop] [--page-cap PAGE_CAP]
```

| Flag | Meaning |
| --- | --- |
| `--rebuild` | Drop & recreate the SQLite database (schema + geo/alias seed) |
| `--quick` | Seed a small subset (first categories × first cities) |
| `--limit N` | Stop after N detail fetches in this run (test use) |
| `--loop` | Run continuously + delta re-crawl of active listings |
| `--page-cap N` | Cap discovered pagination pages per seed |

## One-off runs

```bash
# fresh DB + smoke test
.venv/bin/python -u crawler.py --rebuild --quick --limit 20

# continue from the persistent queue (resumes exactly where it stopped)
.venv/bin/python -u crawler.py --limit 200
```

## 24/7

```bash
# first full run: seeds all categories × all 63 cities when the queue is empty
nohup .venv/bin/python -u crawler.py --loop > logs/crawler.out 2>&1 &

# status
tail -f logs/crawler.log
```

`--loop` behavior:

- Workers run forever; when the queue drains they idle-poll (no busy loop).
- `delta_loop` re-enqueues every `status='active'` listing every
  `DELTA_INTERVAL` (6h) to refresh data and record `price_history` /
  `listing_changes`.
- SIGINT / SIGTERM trigger a graceful shutdown (finish current items, record
  the `crawl_runs` row, close Chrome).

## Process supervision (macOS)

`nohup &` will not restart a crashed process. Use launchd:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.joo.bds-crawler</string>
  <key>ProgramArguments</key>
  <array>
    <string>/absolute/path/to/repo/.venv/bin/python</string>
    <string>-u</string>
    <string>/absolute/path/to/repo/crawler.py</string>
    <string>--loop</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>WorkingDirectory</key><string>/absolute/path/to/repo</string>
  <key>StandardOutPath</key><string>/absolute/path/to/repo/logs/crawler.out</string>
  <key>StandardErrorPath</key><string>/absolute/path/to/repo/logs/crawler.err</string>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.joo.bds-crawler.plist
launchctl start com.joo.bds-crawler
```

## Configuration

`config.py` values; override at runtime via environment variables.

| Env | Default | Purpose |
| --- | --- | --- |
| `BDS_CHROME` | `/Applications/Google Chrome.app/.../Google Chrome` | Chrome binary path |
| `BDS_DB` | `./bds.db` | SQLite database file |
| `BDS_PROFILE` | `/tmp/bds-crawl-current` | Chrome user-data-dir |
| `BDS_PORT` | `9241` | CDP debugging port |
| `BDS_NO_SANDBOX` | `1` | Pass `--no-sandbox` to Chrome |

Also tune in `config.py`: `TABS` (workers), `MAX_REQ_PER_MIN`,
`MIN_INTERVAL`, `DELTA_INTERVAL`, `MAX_ATTEMPTS`.

## Observability

- `logs/crawler.log` — rotating (10 MB × 5).
- `crawl_runs` table — one row per run with pages/new/updated/failures.
- `crawl_queue` — `done` / `pending` / `failed` per URL.
- `unresolved_addresses` — addresses the geo resolver could not map.

## Operational rules

- **One process at a time** (fixed port + shared DB; two instances conflict).
- Watch `logs/crawler.log` for rising `consecutive challenges` — the rate
  limiter already backs off, but sustained challenge spam suggests the source
  IP has degraded; consider a pause or a different egress IP.