# Architecture

## Why a real browser is required

batdongsan.com.vn is protected by a Cloudflare **managed challenge**
(`cf-mitigated: challenge`). Verified empirically:

| Client | Result |
| --- | --- |
| Plain HTTP / curl / curl_cffi + harvested cookie | ❌ 403 — `cf_clearance` is bound to the browser TLS fingerprint |
| Playwright-launched Chromium (headless or headed) | ❌ challenge never auto-passes |
| Plain Chrome `--headless=new` (non-automated) | ❌ challenge never auto-passes |
| **Google Chrome headful, launched plainly, attached over CDP** | ✅ passes |
| Chrome for Testing on macOS host (headful, CDP) | ✅ passes |
| Chrome for Testing inside Docker/Linux (any sandbox config) | ❌ flagged |

The differentiator is the **browser platform + automation mode**. Chrome on
Linux/containers is scored as low-trust by Cloudflare; Chrome on macOS is not.
This is a fingerprint-level decision that cannot be configured away.

## Pipeline

```
1. ChromeSession launches Google Chrome (headful, non-automated)
   with a persistent --user-data-dir and --remote-debugging-port.
2. Playwright connect_over_cdp() attaches to the real browser.
3. Startup waits until the Cloudflare challenge clears (Turnstile auto-passes).
4. N workers (config.TABS=5) pull from the persistent crawl_queue:
     - kind='detail'      -> parse -> upsert listing
     - kind='listing_page'-> discover detail links + pagination -> enqueue
5. RateLimiter gates every fetch: min interval + per-minute cap + backoff.
6. Chrome watchdog relaunches/reconnects the browser on death.
7. --loop mode: delta_loop re-enqueues active listings every DELTA_INTERVAL.
```

## Components

| File | Responsibility |
| --- | --- |
| `crawler.py` | Orchestration: queue, workers, throttle, delta, shutdown |
| `chrome.py` | ChromeSession: launch, CDP attach, watchdog, reconnect |
| `parser.py` | Listing/detail parsing, price/area normalization, `LocResolver` |
| `db.py` | Connection, schema init/rebuild, geo + alias seeding, queue stats |
| `config.py` | Constants + env overrides (`BDS_*`) |
| `schema.sql` | Full SQLite schema + FTS5 + triggers |

## Concurrency model

- **One** Chrome instance, one CDP connection, **one** SQLite connection, all
  inside **one** asyncio event loop. Workers are coroutines; SQLite writes are
  serialized by the single thread (WAL mode, one writer).
- Run exactly **one** crawler process at a time (fixed CDP port, shared DB).
  A supervisor (launchd / systemd) restarts it on crash.

## Geography model

Primary key is the **site's** hierarchy (batdongsan still uses old
districts/wards). Official 2025 administrative units are a normalization layer:

```
cities → districts → wards → streets
                ↑            ↑
        location_aliases (old name → new name, from NQ resolutions)
        unresolved_addresses (manual mapping queue)
```

See [Admin-unit compatibility](../03-operations/admin-compatibility.md).

## Known limitations

- Host-locked to macOS + Google Chrome for the bypass.
- Phone numbers masked by the site.
- Street resolution is heuristic; addresses without a `Đường` marker use the
  first address component as the street (may be a project name).