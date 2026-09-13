# Admin-unit compatibility

## The problem

Vietnam completed a large administrative reform:

- **1 July 2025** — the district level (`quận`/`huyện`/`thị xã`) was abolished
  nationwide (two-tier model: province → ward). Law 72/2025/QH15.
- **Provinces merged** 63 → 34 in 2025.
- **Thousands of wards renamed/merged** via NQ resolutions (e.g. HCM NQ 1685,
  Hanoi NQ 1656, Da Nang NQ 1251, Thanh Hóa NQ 1686).

Example: `Phường 6, Quận 3, TP.HCM` — merged into `Võ Thị Sáu` (2020), then
into **Phường Xuân Hòa** (2025). `Quận 3` no longer exists.

## Design decision

batdongsan.com.vn **still uses the old hierarchy** — listing URLs, filters,
and address text reference old districts/wards. Therefore:

1. **Primary geography = the site's hierarchy** (stable for crawling and
   address matching).
2. **Official 2025 units are a normalization layer only** — never the primary
   key.
3. `location_aliases` maps an old name to the current name. The resolver tries:
   - exact match in the site hierarchy → used;
   - else alias lookup (`old_name` + `old_parent`) → `new_name` matched/inserted
     in the hierarchy;
   - else → logged to `unresolved_addresses` for manual mapping.
4. `districts` is kept (the site uses it) with a `legacy` flag where relevant.

## Seeding aliases

Seed rows in `config.LOCATION_ALIASES` — `(old_name, old_type, old_parent,
new_name, new_type, new_parent, note, source)`:

```python
(("6", "ward", "Quận 3", "Xuân Hòa", "ward", "TP.HCM", "6+7+8->Võ Thị Sáu(2020)->Xuân Hòa(2025)", "NQ1111/NQ1685"),)
```

Names are **bare** (no `Phường`/`Quận` prefix) because the address parser
strips prefixes.

## Adding official GSO data

The current DB seeds 63 site cities with GSO `official_code`. To fully
normalize to the 2025 units, import the official dataset (e.g.
`thanglequoc/vietnamese-provinces-database` — SQL + GIS, versioned by NQ, or
`zuydd/vn-geo`) into `official_code` / `current_name` columns, and expand
`location_aliases` from the NQ merge tables.

## Operational workflow

When the crawler logs new `unresolved_addresses`:

1. Identify the old unit from the raw `address_text`.
2. Look up the NQ resolution (official source) for the new name.
3. Add a `LOCATION_ALIASES` row.
4. Re-run (aliases are seeded idempotently; existing rows are not duplicated).