PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ============ GEOGRAPHY ============
CREATE TABLE cities (
  id            INTEGER PRIMARY KEY,
  code          TEXT UNIQUE,
  name          TEXT NOT NULL,
  slug          TEXT,
  official_code TEXT,           -- legacy GSO code (01=HN, 79=HCM...)
  current_name  TEXT             -- name under the 2025 model (34 provinces)
);

CREATE TABLE districts (
  id            INTEGER PRIMARY KEY,
  city_id       INTEGER NOT NULL REFERENCES cities(id),
  name          TEXT NOT NULL,
  slug          TEXT,
  official_code TEXT,
  legacy        INTEGER DEFAULT 0   -- 1 = district level abolished 1/7/2025
);
CREATE INDEX idx_districts_city_name ON districts (city_id, name);
CREATE INDEX idx_districts_slug ON districts (slug);

CREATE TABLE wards (
  id            INTEGER PRIMARY KEY,
  district_id   INTEGER REFERENCES districts(id),   -- nullable: ward is province-direct (two-tier model)
  city_id       INTEGER NOT NULL REFERENCES cities(id),
  name          TEXT NOT NULL,
  slug          TEXT,
  official_code TEXT
);
CREATE INDEX idx_wards_district_name ON wards (district_id, name);
CREATE INDEX idx_wards_city ON wards (city_id);

CREATE TABLE streets (
  id          INTEGER PRIMARY KEY,
  city_id     INTEGER NOT NULL REFERENCES cities(id),
  district_id INTEGER REFERENCES districts(id),
  ward_id     INTEGER REFERENCES wards(id),
  name        TEXT NOT NULL,
  slug        TEXT
);
CREATE INDEX idx_streets_city_name ON streets (city_id, name);
CREATE INDEX idx_streets_slug ON streets (slug);

-- ============ CATEGORIES ============
CREATE TABLE categories (
  id          INTEGER PRIMARY KEY,
  parent_id   INTEGER REFERENCES categories(id),
  name        TEXT NOT NULL,
  slug        TEXT UNIQUE,
  txn_type  TEXT,
  sort_order  INTEGER
);

-- ============ CORE ============
CREATE TABLE agents (
  id            TEXT PRIMARY KEY,
  name          TEXT,
  profile_url   TEXT,
  product_type  INTEGER,
  cate_id       INTEGER,
  project_id    INTEGER,
  city_code     TEXT,
  district_id   INTEGER,
  created_at    TEXT DEFAULT (datetime('now')),
  updated_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE listings (
  id            INTEGER PRIMARY KEY,
  url           TEXT UNIQUE NOT NULL,
  title         TEXT NOT NULL,
  category_id   INTEGER REFERENCES categories(id),
  listing_type  TEXT,
  price_text    TEXT,
  price_vnd     INTEGER,
  price_per_m2  REAL,
  area_m2       REAL,
  bedrooms      INTEGER,
  bathrooms     INTEGER,
  floors        INTEGER,
  facade_m      REAL,
  road_m        REAL,
  direction     TEXT,
  balcony_dir   TEXT,
  legal_status  TEXT,
  interior      TEXT,
  address_text  TEXT,
  street        TEXT,
  city_id       INTEGER REFERENCES cities(id),
  district_id   INTEGER REFERENCES districts(id),
  ward_id       INTEGER REFERENCES wards(id),
  street_id     INTEGER REFERENCES streets(id),
  gps_lat       REAL,
  gps_lng       REAL,
  posted_at     TEXT,
  expiry_at     TEXT,
  tier          TEXT,
  status        TEXT DEFAULT 'active',
  agent_id      TEXT REFERENCES agents(id),
  published_at  TEXT,
  modified_at   TEXT,
  description   TEXT,
  specs         TEXT DEFAULT '{}',
  first_seen_at TEXT,
  last_seen_at  TEXT,
  created_at    TEXT DEFAULT (datetime('now')),
  updated_at    TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_listings_city ON listings (city_id);
CREATE INDEX idx_listings_district ON listings (district_id);
CREATE INDEX idx_listings_ward ON listings (ward_id);
CREATE INDEX idx_listings_street ON listings (street_id);
CREATE INDEX idx_listings_category ON listings (category_id);
CREATE INDEX idx_listings_price ON listings (price_vnd);
CREATE INDEX idx_listings_status ON listings (status);

CREATE TABLE listing_images (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  listing_id  INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
  url         TEXT NOT NULL,
  seq         INTEGER,
  is_primary  INTEGER DEFAULT 0,
  crawled_at  TEXT DEFAULT (datetime('now')),
  UNIQUE (listing_id, url)
);
CREATE INDEX idx_listing_images_lid ON listing_images (listing_id);

CREATE TABLE listing_videos (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  listing_id  INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
  url         TEXT NOT NULL,
  thumb_url   TEXT,
  crawled_at  TEXT DEFAULT (datetime('now')),
  UNIQUE (listing_id, url)
);

CREATE TABLE price_history (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  listing_id    INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
  price_text    TEXT,
  price_vnd     INTEGER,
  price_per_m2  REAL,
  area_m2       REAL,
  captured_at   TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_price_history ON price_history (listing_id, captured_at);

CREATE TABLE listing_changes (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  listing_id  INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
  field       TEXT,
  old_value   TEXT,
  new_value   TEXT,
  changed_at  TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_listing_changes ON listing_changes (listing_id, changed_at);

-- ============ ADMIN COMPATIBILITY ============
-- map old units (merged/renamed) -> current name
CREATE TABLE location_aliases (
  id          INTEGER PRIMARY KEY,
  old_name    TEXT NOT NULL,
  old_type    TEXT,             -- ward | district | city
  old_parent  TEXT,             -- old parent context (e.g. "Quận 3"), nullable
  new_name    TEXT NOT NULL,
  new_type    TEXT,
  new_parent  TEXT,
  note        TEXT,
  source      TEXT,             -- NQ1111 | NQ1685 | NQ1656 ...
  created_at  TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_aliases_old ON location_aliases (old_name, old_parent);

-- addresses that failed to resolve -> manual mapping log
CREATE TABLE unresolved_addresses (
  id           INTEGER PRIMARY KEY,
  address_text TEXT,
  city_hint    TEXT,
  reason       TEXT,
  listing_url  TEXT,
  seen_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE raw_snapshots (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  listing_id  INTEGER REFERENCES listings(id) ON DELETE CASCADE,
  payload     TEXT,
  captured_at TEXT DEFAULT (datetime('now'))
);

-- ============ CRAWL BOOKKEEPING ============
CREATE TABLE crawl_queue (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  url             TEXT UNIQUE NOT NULL,
  kind            TEXT,
  status          TEXT DEFAULT 'pending',
  attempts        INTEGER DEFAULT 0,
  last_error      TEXT,
  last_attempt_at TEXT
);
CREATE INDEX idx_queue_status ON crawl_queue (status);

CREATE TABLE crawl_runs (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at       TEXT,
  finished_at      TEXT,
  status           TEXT,
  pages_fetched    INTEGER DEFAULT 0,
  listings_new     INTEGER DEFAULT 0,
  listings_updated INTEGER DEFAULT 0,
  failures         INTEGER DEFAULT 0
);

-- ============ FTS5 SEARCH ============
CREATE VIRTUAL TABLE listings_fts USING fts5(title, description, content='listings', content_rowid='id');

CREATE TRIGGER listings_ai AFTER INSERT ON listings BEGIN
  INSERT INTO listings_fts (rowid, title, description) VALUES (new.id, new.title, new.description);
END;
CREATE TRIGGER listings_ad AFTER DELETE ON listings BEGIN
  INSERT INTO listings_fts (listings_fts, rowid, title, description) VALUES ('delete', old.id, old.title, old.description);
END;
CREATE TRIGGER listings_au AFTER UPDATE ON listings BEGIN
  INSERT INTO listings_fts (listings_fts, rowid, title, description) VALUES ('delete', old.id, old.title, old.description);
  INSERT INTO listings_fts (rowid, title, description) VALUES (new.id, new.title, new.description);
END;