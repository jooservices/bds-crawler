# Data model

Full schema in [`schema.sql`](../../schema.sql). SQLite, WAL mode, foreign keys
enabled per connection.

## Core

`listings` — one row per listing (`id` = the site's `Mã tin`).

- Normalized numeric columns: `price_vnd`, `price_per_m2`, `area_m2`,
  `bedrooms`, `bathrooms`, `floors`, `facade_m`, `road_m`, `gps_lat`,
  `gps_lng`.
- Text/display columns kept as the site shows them: `price_text`,
  `address_text`, `tier`, `direction`, `legal_status`, `interior`.
- `specs` — full original spec map as JSON (KISS; fields vary by listing type).
- `status` — `active` / `expired` / `removed`.
- `first_seen_at` / `last_seen_at` for delta tracking.

## Geography

```
cities (63, site slugs + official_code)
  └─ districts (site names; legacy flag = 2025 two-tier)
       └─ wards (district_id nullable — city-direct wards)
streets (city_id + optional district_id/ward_id; heuristic)
```

No `UNIQUE` on district/ward/street names — duplicates are permitted within a
city (real-world repeated names). Lookup is by `(parent_id, name)` with an
index.

## Admin compatibility

- `location_aliases` — old admin-unit name → current name (source: NQ
  resolutions). Used as a fallback when a ward name is not found in the site
  hierarchy.
- `unresolved_addresses` — addresses the resolver could not map (manual queue).

See [Admin-unit compatibility](admin-compatibility.md).

## Change tracking

- `price_history` — one row per observed price (inserted on new listing and on
  price change). Query `GROUP BY listing_id HAVING COUNT(*) > 1` for price
  movers.
- `listing_changes` — field-level diff log (`price`, `status`, `area`).

## Media & snapshots

- `listing_images` / `listing_videos` — gallery media with ordering.
- `raw_snapshots` — full extraction JSON per crawl (re-analysis without
  re-crawling). Grows unbounded — archive or prune periodically.

## Crawl bookkeeping

- `crawl_queue` — URL, `kind` (`detail` | `listing_page`), `status`
  (`pending` | `done` | `failed`), `attempts`, `last_error`.
- `crawl_runs` — per-process summary.

## Search

`listings_fts` — FTS5 external-content table over `title` + `description`,
kept in sync by triggers on `listings`:

```sql
SELECT l.* FROM listings_fts f
JOIN listings l ON l.id = f.rowid
WHERE listings_fts MATCH 'chung' ;
```

## Useful queries

```sql
-- price movers
SELECT listing_id, COUNT(*) n FROM price_history
GROUP BY listing_id HAVING n > 1;

-- listings on a street
SELECT * FROM listings WHERE street_id = ?;

-- unresolved geography
SELECT address_text, reason, COUNT(*) FROM unresolved_addresses
GROUP BY address_text, reason;