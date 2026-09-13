"""DB helpers: connect, init/rebuild, seed geo + queue."""

import os
import sqlite3
import time

import config


def connect():
    con = sqlite3.connect(config.DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    con.execute("PRAGMA busy_timeout = 30000")
    return con


def init_db(force=False):
    if force and os.path.exists(config.DB):
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(str(config.DB) + suffix)
            except OSError:
                pass
    con = connect()
    has = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cities'").fetchone()
    if has is None:
        con.executescript(config.SCHEMA.read_text())
        con.commit()
    return con


def seed_geo(con):
    n = con.execute("SELECT COUNT(*) FROM cities").fetchone()[0]
    if n == 0:
        for code, name, slug, official in config.CITIES:
            con.execute(
                "INSERT INTO cities (code, name, slug, official_code) VALUES (?,?,?,?)",
                (code or None, name, slug, official or None),
            )
    c = con.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    if c == 0:
        ids = {}
        for i, (slug, (name, txn, _parent)) in enumerate(config.CATEGORIES.items()):
            cur = con.execute(
                "INSERT INTO categories (name, slug, txn_type, parent_id, sort_order) VALUES (?,?,?,?,?)",
                (name, slug, txn, None, i),
            )
            ids[slug] = cur.lastrowid
        for slug, (_name, _txn, parent) in config.CATEGORIES.items():
            if parent:
                con.execute("UPDATE categories SET parent_id=? WHERE slug=?", (ids[parent], slug))
    con.commit()


def seed_aliases(con):
    n = con.execute("SELECT COUNT(*) FROM location_aliases").fetchone()[0]
    if n == 0:
        con.executemany(
            "INSERT INTO location_aliases (old_name, old_type, old_parent, new_name, new_type, new_parent, note, source) VALUES (?,?,?,?,?,?,?,?)",
            config.LOCATION_ALIASES,
        )
    con.commit()


def seed_queue(con, quick=False, cats_limit=4, cities_limit=3, page_cap=None):
    """Enqueue page-1 listing URLs for each leaf category x city."""
    cats = [s for s, (_, _, p) in config.CATEGORIES.items() if p is not None]
    cities = [c[2] for c in config.CITIES]
    if quick:
        cats = cats[:cats_limit]
        cities = cities[:cities_limit]
    rows = []
    for cat in cats:
        for city in cities:
            rows.append((f"https://batdongsan.com.vn/{cat}-{city}", "listing_page"))
    con.executemany("INSERT OR IGNORE INTO crawl_queue (url, kind, status) VALUES (?,?, 'pending')", rows)
    con.commit()
    return len(rows)


def queue_stats(con):
    rows = con.execute("SELECT status, COUNT(*) n FROM crawl_queue GROUP BY status").fetchall()
    return {r["status"]: r["n"] for r in rows}


def start_run(con):
    cur = con.execute(
        "INSERT INTO crawl_runs (started_at, status, pages_fetched, listings_new, listings_updated, failures) "
        "VALUES (?, 'running', 0,0,0,0)",
        (time.strftime("%Y-%m-%d %H:%M:%S"),),
    )
    con.commit()
    return cur.lastrowid


def finish_run(con, run_id, stats, status="done"):
    con.execute(
        "UPDATE crawl_runs SET finished_at=?, status=?, pages_fetched=?, listings_new=?, listings_updated=?, failures=? WHERE id=?",
        (
            time.strftime("%Y-%m-%d %H:%M:%S"),
            status,
            stats.get("pages", 0),
            stats.get("new", 0),
            stats.get("updated", 0),
            stats.get("failures", 0),
            run_id,
        ),
    )
    con.commit()
