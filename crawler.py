"""JOOservices batdongsan crawler - queue-based 24/7-ready (single file).

Features:
- Persistent SQLite queue (crawl_queue) -> resume after crash
- Throttle: min interval + per-minute cap + exponential backoff on challenge
- Chrome watchdog: auto-relaunch on death
- Full upsert: listings, images, videos, agents, price_history, listing_changes, raw_snapshots
- Delta mode: re-crawl active listings periodically (--loop)
- Logging to file + console, crawl_runs tracking, graceful shutdown
"""
import argparse
import asyncio
import json
import logging
import logging.handlers
import signal
import sys
import time
from collections import deque

from playwright.async_api import async_playwright

import config
import db as dbmod
from chrome import ChromeSession
from parser import LocResolver, match_category, parse_detail, parse_listing_page

logger = logging.getLogger("bds")


def setup_logging():
    config.LOG_DIR.mkdir(exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fh = logging.handlers.RotatingFileHandler(config.LOG_FILE, maxBytes=10_000_000, backupCount=5)
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root = logging.getLogger("bds")
    root.setLevel(logging.INFO)
    root.addHandler(fh)
    root.addHandler(sh)


class RateLimiter:
    def __init__(self, min_interval, max_per_min):
        self.min_interval = min_interval
        self.max_per_min = max_per_min
        self.lock = asyncio.Lock()
        self.last = 0.0
        self.times = deque()
        self.pause_until = 0.0
        self.consec_challenge = 0

    async def acquire(self):
        async with self.lock:
            now = time.time()
            if self.pause_until > now:
                wait = self.pause_until - now
            else:
                while self.times and now - self.times[0] > 60:
                    self.times.popleft()
                if len(self.times) >= self.max_per_min:
                    wait = self.times[0] + 60 - now
                else:
                    wait = max(0.0, self.min_interval - (now - self.last))
        if wait > 0:
            await asyncio.sleep(wait)
        async with self.lock:
            now = time.time()
            self.last = now
            self.times.append(now)

    async def backoff(self, hard=False):
        async with self.lock:
            self.consec_challenge += 1
            d = (60 if hard else 10) * self.consec_challenge
            self.pause_until = time.time() + min(d, 1800)
            logger.warning("backoff %ss (consecutive challenges=%d)", d, self.consec_challenge)

    def note_ok(self):
        self.consec_challenge = 0


class Crawler:
    def __init__(self, args):
        self.args = args
        self.con = None
        self.session = ChromeSession()
        self.pw = None
        self.limiter = RateLimiter(config.MIN_INTERVAL, config.MAX_REQ_PER_MIN)
        self.stop = asyncio.Event()
        self.active_work = 0
        self.claim_lock = asyncio.Lock()
        self.stats = {"pages": 0, "new": 0, "updated": 0, "failures": 0, "details": 0}
        self.run_id = None
        self.resolver = None
        self.cats_cache = None

    # ---------- queue ----------
    def claim(self):
        # prefer detail first (goal = crawl listings); listing pages after
        row = self.con.execute(
            "SELECT id, url, kind FROM crawl_queue "
            "WHERE status='pending' AND attempts < ? AND kind='detail' ORDER BY id LIMIT 1",
            (config.MAX_ATTEMPTS,),
        ).fetchone()
        if row is None:
            row = self.con.execute(
                "SELECT id, url, kind FROM crawl_queue "
                "WHERE status='pending' AND attempts < ? AND kind!='detail' ORDER BY id LIMIT 1",
                (config.MAX_ATTEMPTS,),
            ).fetchone()
        if row:
            self.con.execute("UPDATE crawl_queue SET status='in_progress', last_attempt_at=? WHERE id=?", (time.strftime("%Y-%m-%d %H:%M:%S"), row["id"]))
            self.con.commit()
            return dict(row)
        return None

    def mark(self, qid, ok, error=""):
        if ok:
            self.con.execute("UPDATE crawl_queue SET status='done', last_error=NULL WHERE id=?", (qid,))
        else:
            row = self.con.execute("SELECT attempts FROM crawl_queue WHERE id=?", (qid,)).fetchone()
            a = (row["attempts"] if row else 0) + 1
            if a >= config.MAX_ATTEMPTS:
                self.con.execute("UPDATE crawl_queue SET status='failed', attempts=?, last_error=?, last_attempt_at=? WHERE id=?", (a, error[:300], time.strftime("%Y-%m-%d %H:%M:%S"), qid))
            else:
                self.con.execute("UPDATE crawl_queue SET status='pending', attempts=?, last_error=?, last_attempt_at=? WHERE id=?", (a, error[:300], time.strftime("%Y-%m-%d %H:%M:%S"), qid))
        self.con.commit()

    def enqueue(self, url, kind):
        self.con.execute("INSERT OR IGNORE INTO crawl_queue (url, kind, status) VALUES (?,?,'pending')", (url, kind))

    def enqueue_pages(self, base_url, max_page, cap=None):
        for p in range(2, max_page + 1):
            if cap and p > cap:
                break
            self.enqueue(f"{base_url}/p{p}", "listing_page")

    # ---------- fetch ----------
    async def fetch(self, wid, url, is_detail):
        await self.limiter.acquire()
        for attempt in range(3):
            try:
                await self.session.ensure(self.pw)
                page = await self.session.get_page(wid)
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                if is_detail:
                    try:
                        await page.wait_for_selector("div.re__pr-short-info-item", timeout=8000)
                    except Exception:
                        pass
                await page.wait_for_timeout(700)
                html = await page.content()
                if "Chờ một chút" in html or "Just a moment" in html:
                    cleared = await self._wait_clearance(page)
                    if not cleared:
                        await self.limiter.backoff()
                        return None, "challenge"
                    html = await page.content()
                if len(html) < 20000:
                    return None, f"short({len(html)})"
                self.limiter.note_ok()
                return html, None
            except Exception as e:
                msg = str(e)[:120]
                # browser-level issue -> watchdog (invalidate stale connection, then reconnect)
                if any(x in msg for x in ("has been closed", "Connection closed", "Target closed", "Target crashed", "context, or browser")):
                    self.session.invalidate()
                try:
                    await self.session.ensure(self.pw)
                    await self.session.reset_page(wid)
                except Exception:
                    pass
                if attempt < 2:
                    await asyncio.sleep(1 + attempt * 2)
                    continue
                return None, msg
        return None, "unknown"

    async def _wait_clearance(self, page, timeout=config.CHALLENGE_WAIT):
        t0 = time.time()
        while time.time() - t0 < timeout:
            await page.wait_for_timeout(2000)
            try:
                html = await page.content()
            except Exception:
                html = ""
            if "Chờ một chút" not in html and "Just a moment" not in html and len(html) > 20000:
                return True
        return False

    # ---------- processing ----------
    def process_listing_page(self, url, html):
        links, max_page = parse_listing_page(html, url)
        for l in links:
            self.enqueue(l, "detail")
        base = url.split("/p")[0] if "/p" in url else url
        cap = self.args.page_cap
        self.enqueue_pages(base, max_page, cap=cap)
        return len(links)

    def upsert_listing(self, rec, category_id, txn):
        listing_id = rec["listing_id"]
        if not listing_id:
            m = __import__("re").search(r"-pr(\d+)", rec["url"])
            listing_id = m.group(1) if m else None
        if not listing_id:
            return None
        listing_id = int(listing_id)
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        # agent first (listings.agent_id FK)
        if rec["agent_id"]:
            a = self.con.execute("SELECT id FROM agents WHERE id=?", (rec["agent_id"],)).fetchone()
            params = dict(p.split("=") for p in rec["agent_params"].lstrip("?").split("&") if "=" in p) if rec["agent_params"] else {}
            if a is None:
                self.con.execute(
                    "INSERT INTO agents (id, name, profile_url, product_type, cate_id, project_id, city_code, district_id, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (rec["agent_id"], rec["agent_name"], rec["agent_url"],
                     params.get("productType"), params.get("cateId"), params.get("projectId"),
                     params.get("cityCode"), params.get("districtId"), now, now),
                )
            else:
                self.con.execute("UPDATE agents SET name=?, profile_url=?, updated_at=? WHERE id=?",
                                 (rec["agent_name"], rec["agent_url"], now, rec["agent_id"]))

        existing = self.con.execute("SELECT * FROM listings WHERE id=?", (listing_id,)).fetchone()

        status = "active"
        if rec["expiry_at"]:
            try:
                if time.strptime(rec["expiry_at"], "%d/%m/%Y") < time.strptime(time.strftime("%d/%m/%Y"), "%d/%m/%Y"):
                    status = "expired"
            except ValueError:
                pass

        if existing is None:
            self.con.execute(
                """INSERT INTO listings (id, url, title, category_id, listing_type, price_text, price_vnd,
                   price_per_m2, area_m2, bedrooms, bathrooms, floors, facade_m, road_m, direction, balcony_dir,
                   legal_status, interior, address_text, street, city_id, district_id, ward_id, street_id,
                   gps_lat, gps_lng, posted_at, expiry_at, tier, status, agent_id, published_at, modified_at,
                   description, specs, first_seen_at, last_seen_at, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (listing_id, rec["url"], rec["title"], category_id, txn, rec["price_text"], rec["price_vnd"],
                 rec["price_per_m2"], rec["area_m2"], rec["bedrooms"], rec["bathrooms"], rec["floors"],
                 rec["facade_m"], rec["road_m"], rec["direction"], rec["balcony_dir"], rec["legal_status"],
                 rec["interior"], rec["address_text"], rec["street_text"], rec["city_id"], rec["district_id"],
                 rec["ward_id"], rec["street_id"], rec["gps_lat"], rec["gps_lng"], rec["posted_at"],
                 rec["expiry_at"], rec["tier"], status, rec["agent_id"] or None, rec["published_at"], rec["modified_at"],
                 rec["description"], json.dumps(rec["specs"], ensure_ascii=False), now, now, now, now),
            )
            self.con.execute(
                "INSERT INTO price_history (listing_id, price_text, price_vnd, price_per_m2, area_m2, captured_at) VALUES (?,?,?,?,?,?)",
                (listing_id, rec["price_text"], rec["price_vnd"], rec["price_per_m2"], rec["area_m2"], now),
            )
            self.stats["new"] += 1
        else:
            changes = []
            for field, old, new in (
                ("price", existing["price_text"], rec["price_text"]),
                ("status", existing["status"], status),
                ("area", existing["area_m2"], rec["area_m2"]),
            ):
                if str(old) != str(new):
                    changes.append((field, old, new))
            if changes:
                for field, old, new in changes:
                    self.con.execute(
                        "INSERT INTO listing_changes (listing_id, field, old_value, new_value, changed_at) VALUES (?,?,?,?,?)",
                        (listing_id, field, str(old), str(new), now),
                    )
                if any(c[0] == "price" for c in changes):
                    self.con.execute(
                        "INSERT INTO price_history (listing_id, price_text, price_vnd, price_per_m2, area_m2, captured_at) VALUES (?,?,?,?,?,?)",
                        (listing_id, rec["price_text"], rec["price_vnd"], rec["price_per_m2"], rec["area_m2"], now),
                    )
            self.con.execute(
                """UPDATE listings SET url=?, title=?, category_id=?, listing_type=?, price_text=?, price_vnd=?,
                   price_per_m2=?, area_m2=?, bedrooms=?, bathrooms=?, floors=?, facade_m=?, road_m=?, direction=?,
                   balcony_dir=?, legal_status=?, interior=?, address_text=?, street=?, city_id=?, district_id=?,
                   ward_id=?, street_id=?, gps_lat=?, gps_lng=?, posted_at=?, expiry_at=?, tier=?, status=?,
                   agent_id=?, published_at=?, modified_at=?, description=?, specs=?, last_seen_at=?, updated_at=?
                   WHERE id=?""",
                (rec["url"], rec["title"], category_id, txn, rec["price_text"], rec["price_vnd"],
                 rec["price_per_m2"], rec["area_m2"], rec["bedrooms"], rec["bathrooms"], rec["floors"],
                 rec["facade_m"], rec["road_m"], rec["direction"], rec["balcony_dir"], rec["legal_status"],
                 rec["interior"], rec["address_text"], rec["street_text"], rec["city_id"], rec["district_id"],
                 rec["ward_id"], rec["street_id"], rec["gps_lat"], rec["gps_lng"], rec["posted_at"],
                 rec["expiry_at"], rec["tier"], status, rec["agent_id"] or None, rec["published_at"], rec["modified_at"],
                 rec["description"], json.dumps(rec["specs"], ensure_ascii=False), now, now, listing_id),
            )
            self.stats["updated"] += 1

        # images / videos
        for i, u in enumerate(rec["images"]):
            self.con.execute(
                "INSERT OR IGNORE INTO listing_images (listing_id, url, seq, is_primary) VALUES (?,?,?,?)",
                (listing_id, u, i, 1 if i == 0 else 0),
            )
        for v in rec["video"]:
            self.con.execute(
                "INSERT OR IGNORE INTO listing_videos (listing_id, url, thumb_url) VALUES (?,?,?)",
                (listing_id, v, rec["video_thumb"]),
            )

        # snapshot
        self.con.execute("INSERT INTO raw_snapshots (listing_id, payload) VALUES (?,?)",
                         (listing_id, json.dumps(rec, ensure_ascii=False)))
        return listing_id

    # ---------- worker ----------
    async def worker(self, wid):
        logger.info("worker %d started", wid)
        while not self.stop.is_set():
            item = await self._claim_async()
            if item is None:
                await asyncio.sleep(2)
                if self.active_work == 0 and not self.args.loop:
                    # queue drained
                    logger.info("worker %d: queue drained, exiting", wid)
                    break
                continue
            url, kind = item["url"], item["kind"]
            self.active_work += 1
            try:
                ok, error = await self._handle(url, kind, wid)
            except Exception as e:
                # crash-safe: unexpected handler error -> mark failed, worker survives
                ok, error = False, f"handler_error: {str(e)[:150]}"
                logger.exception("worker %d crashed on %s", wid, url)
            finally:
                self.active_work -= 1
            self.mark(item["id"], ok, error)
            if self.args.limit and self.stats["details"] >= self.args.limit:
                self.stop.set()
                break
        logger.info("worker %d stopped", wid)

    async def _claim_async(self):
        async with self.claim_lock:
            return self.claim()

    async def _handle(self, url, kind, wid):
        is_detail = kind == "detail"
        html, err = await self.fetch(wid, url, is_detail)
        if err:
            self.stats["failures"] += 1
            logger.warning("FAIL %s %s -> %s", kind, url, err)
            return False, err
        self.stats["pages"] += 1
        if kind == "listing_page":
            n = self.process_listing_page(url, html)
            logger.info("listing_page %s -> %d links", url, n)
        else:
            cat_id = match_category(self.con, url, cache=self.cats_cache)
            txn = None
            if cat_id:
                r = self.con.execute("SELECT txn_type FROM categories WHERE id=?", (cat_id,)).fetchone()
                txn = r["txn_type"] if r else None
            rec = parse_detail(html, url, resolver=self.resolver)
            lid = self.upsert_listing(rec, cat_id, txn)
            self.stats["details"] += 1
            logger.info("detail %s -> id=%s price=%s", url, lid, rec["price_text"])
        self.con.commit()
        return True, ""

    # ---------- delta ----------
    async def delta_loop(self):
        while not self.stop.is_set():
            await asyncio.sleep(config.DELTA_INTERVAL)
            if self.stop.is_set():
                break
            n_active = self.con.execute("SELECT COUNT(*) c FROM listings WHERE status='active'").fetchone()["c"]
            urls = [r["url"] for r in self.con.execute("SELECT url FROM listings WHERE status='active'")]
            for u in urls:
                self.enqueue(u, "detail")
            self.con.commit()
            logger.info("delta: re-enqueued %d active listings", n_active)

    # ---------- main ----------
    async def run(self):
        self.con = dbmod.init_db(force=self.args.rebuild)
        dbmod.seed_geo(self.con)
        dbmod.seed_aliases(self.con)
        q0 = dbmod.queue_stats(self.con)
        if self.args.rebuild or sum(q0.values()) == 0:
            dbmod.seed_queue(self.con, quick=self.args.quick)
        stats0 = dbmod.queue_stats(self.con)
        logger.info("queue: %s", stats0)
        self.resolver = LocResolver(self.con)
        self.cats_cache = list(self.con.execute("SELECT id, slug, txn_type FROM categories"))
        # reset items stuck in_progress from a previous (crashed) run -> re-crawl
        n_reset = self.con.execute("UPDATE crawl_queue SET status='pending' WHERE status='in_progress'").rowcount
        if n_reset:
            logger.info("reset %d stuck in_progress items", n_reset)
        self.con.commit()

        self.pw = await async_playwright().start()
        await self.session.ensure(self.pw)
        # wait clearance
        for i in range(30):
            page = await self.session.get_page(0)
            try:
                await page.goto(config.WARMUP, wait_until="domcontentloaded", timeout=45000)
            except Exception:
                pass
            if await self._wait_clearance(page, 3):
                logger.info("Cloudflare clearance OK after %ds", (i + 1) * 3)
                break
        else:
            logger.warning("Cloudflare clearance not confirmed")

        self.run_id = dbmod.start_run(self.con)
        workers = [asyncio.create_task(self.worker(i)) for i in range(config.TABS)]
        delta_task = asyncio.create_task(self.delta_loop()) if self.args.loop else None

        try:
            await asyncio.gather(*workers)
        except asyncio.CancelledError:
            logger.info("cancelled")
        finally:
            if delta_task:
                delta_task.cancel()
            dbmod.finish_run(self.con, self.run_id, self.stats, status="done" if not self.stop.is_set() else "interrupted")
            logger.info("run finished: %s", self.stats)
            await self.session.close()
            self.con.close()
            await self.pw.stop()


def _signal(crawler):
    def handler(signum, frame):
        logger.info("signal %s -> graceful shutdown", signum)
        crawler.stop.set()
    return handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true", help="drop & recreate DB")
    parser.add_argument("--quick", action="store_true", help="small seed (limited cats/cities)")
    parser.add_argument("--limit", type=int, default=0, help="max details to fetch this run")
    parser.add_argument("--loop", action="store_true", help="continuous + delta re-crawl")
    parser.add_argument("--page-cap", type=int, default=None, help="max pagination pages per seed")
    args = parser.parse_args()

    setup_logging()
    crawler = Crawler(args)
    signal.signal(signal.SIGINT, _signal(crawler))
    signal.signal(signal.SIGTERM, _signal(crawler))
    asyncio.run(crawler.run())


if __name__ == "__main__":
    main()