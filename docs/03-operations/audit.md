# Audit report

Audit scope: correctness, performance, security, and robustness of the crawler
(code as of the current working tree).

## Verified on real data (macOS host)

| Check | Result |
| --- | --- |
| Cloudflare bypass (headful Chrome + CDP) | ✅ passes; clearance ~3 s |
| Crawl run (quick + HCM targeted) | ✅ 156 listings, 0 fetch failures |
| Field completeness | ✅ 156/156 title, price, area, address, GPS, tier, description, category |
| Geo resolution | ✅ city 156/156; district 155; ward 156; street 155 |
| Admin alias on real data | ✅ `Võ Thị Sáu, Q3` → `Xuân Hòa`; `Phường 9, Q3` → `Nhiêu Lộc` |
| Price normalization | ✅ `10,8 tỷ` → `10_800_000_000` |
| `price_history` | ✅ row per listing; no duplicate on unchanged re-crawl |
| FTS5 search | ✅ `MATCH 'chung'` returns rows |
| Resume after crash | ✅ queue persists; orphaned `in_progress` reset on startup |
| Graceful shutdown | ✅ SIGINT/SIGTERM → clean close, `crawl_runs` recorded |

## Issues found & fixed in this audit

1. **Worker crash-safety** — an uncaught handler exception left the item stuck
   `in_progress` forever and silently killed a worker. Fixed: `_handle` is
   wrapped in try/except, the item is marked `failed`, the worker survives.
2. **Orphaned `in_progress` rows** — items stuck from a previous crash were
   never re-queued. Fixed: startup resets `in_progress → pending`.
3. **Queue re-seeding on every restart** — the full seed (1386 URLs) re-ran on
   each start and re-ballooned the queue. Fixed: seed only when the queue is
   empty (or on `--rebuild`).
4. **`wards.district_id NOT NULL`** — addresses without a parsed district
   failed FK. Fixed: column nullable.
5. **Watchdog stale connection** — when the CDP websocket died, `ensure()` did
   not reconnect (stale `browser` object) and every request failed. Fixed:
   `invalidate()` + reconnect on browser-level errors.
6. **SQLite keyword `transaction`** — renamed to `txn_type`.
7. **FK ordering** — agents inserted before listings.

## Performance

- ~1 page/s with 5 tabs at the configured throttle (site-limited; challenges
  appear above ~40 req/min from one IP).
- `match_category` now uses a cached category list (was a query per detail).
- SQLite WAL, single writer, indexed FK columns.

## Security

- All queries parameterized — no injection surface.
- Crawl URLs derive from config seeds + relative links resolved against the
  trusted host — no SSRF from page content.
- No secrets in the codebase; runtime config via `BDS_*` env vars.
- Stored data is public listing data; phone numbers are masked by the source.

## Residual risks

| Risk | Note |
| --- | --- |
| Source IP degradation | Sustained challenge spam → backoff caps at 30 min; ops should watch logs |
| `raw_snapshots` growth | Unbounded; add retention/pruning for long 24/7 runs |
| Site markup changes | Regex parsers keyed to CSS classes; a site redesign breaks fields (raw HTML + specs JSONB preserve data) |
| Linux/container bypass | Not supported — Cloudflare flags Linux Chrome |
| Street heuristic | Addresses without `Đường` use the first component (may be a project name) |

## Recommendation

Run 24/7 with the launchd supervisor (one process), watch `logs/crawler.log`
for backoff events, and add `raw_snapshots` pruning before production scale.