"""Parsers: listing page, detail page, price/area normalization, location resolution."""

import json
import re
import unicodedata
from urllib.parse import urljoin


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


def slugify(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower().replace("đ", "d")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def normalize_float(text):
    if not text:
        return None
    t = clean(text).lower().replace("m²", "").replace("m2", "").replace(" ", "")
    m = re.search(r"[\d.,]+", t)
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", "."))
    except ValueError:
        return None


def parse_price_vnd(text):
    """'27 tỷ' -> 27_000_000_000 ; '450 triệu/m²' -> per-m2 excluded ; thỏa thuận -> None."""
    if not text:
        return None
    t = clean(text).lower()
    if any(x in t for x in ("thỏa thuận", "thoả thuận", "thương lượng")):
        return None
    t = re.split(r"/", t)[0].strip()
    m = re.search(r"([\d.,]+)", t)
    if not m:
        return None
    try:
        val = float(m.group(1).replace(".", "").replace(",", "."))
    except ValueError:
        return None
    mult = 1
    if "tỷ" in t or "tỉ" in t:
        mult = 1_000_000_000
    elif "triệu" in t or "tr " in t or t.endswith("tr"):
        mult = 1_000_000
    elif "nghìn" in t:
        mult = 1_000
    return int(val * mult)


# ---------- listing page ----------
def parse_listing_page(html, base_url):
    links = {urljoin(base_url, m.group(1)) for m in re.finditer(r'href="(/[^"]*-pr\d+)"', html)}
    max_page = 1
    for m in re.finditer(r'href="([^"]*/p(\d+))"', html):
        try:
            n = int(m.group(2))
        except ValueError:
            continue
        max_page = max(max_page, n)
    return links, max_page


# ---------- detail page ----------
def _specs(html):
    specs = {}
    for m in re.finditer(
        r're__pr-short-info-item[^"]*"[^>]*>.*?<span class="title">(.*?)</span>\s*<span class="value">(.*?)</span>',
        html,
        re.DOTALL,
    ):
        k, v = clean(re.sub(r"<[^>]+>", "", m.group(1))), clean(re.sub(r"<[^>]+>", "", m.group(2)))
        if k and v:
            specs[k] = v
    for m in re.finditer(
        r're__pr-specs-content-item">.*?re__pr-specs-content-item-title">(.*?)</span>\s*<span class="re__pr-specs-content-item-value">(.*?)</span>',
        html,
        re.DOTALL,
    ):
        k, v = clean(re.sub(r"<[^>]+>", "", m.group(1))), clean(re.sub(r"<[^>]+>", "", m.group(2)))
        if k and v:
            specs[k] = v
    return specs


def parse_detail(html, url, resolver=None, city_hint=None):
    def txt(pattern, flags=re.DOTALL):
        m = re.search(pattern, html, flags)
        return clean(re.sub(r"<[^>]+>", " ", m.group(1))) if m else ""

    specs = _specs(html)
    price_text = next((v for k, v in specs.items() if "giá" in k.lower()), "")
    area_text = specs.get("Diện tích", "")
    posted = next((v for k, v in specs.items() if "đăng" in k.lower()), "")
    expiry = next((v for k, v in specs.items() if "hết hạn" in k.lower()), "")
    listing_id = next((v for k, v in specs.items() if "mã tin" in k.lower()), "")
    tier = next((v for k, v in specs.items() if "loại tin" in k.lower()), "")

    ppm_text = ""
    ppm_m = re.search(r"([\d.,]+\s*(?:triệu|tỷ)\s*/m²?)", html)
    if ppm_m:
        ppm_text = clean(ppm_m.group(1))

    address = txt(r're__ldp-address.*?<span class="re__address"[^>]*>(.*?)</span>')

    images = re.findall(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html)
    if not images:
        images = list(
            dict.fromkeys(
                re.findall(
                    r'https://file\d?\.batdongsan\.com\.vn/(?:resize|origin)?/?[^"\s#]+?\.(?:jpg|jpeg|png|webp)', html
                )
            )
        )
    video = [
        u
        for u in dict.fromkeys(re.findall(r'https://[^"\s]+?\.mp4[^"\s]*', html))
        if "#~" not in u and "&quot;" not in u
    ]
    vt = re.search(r'https://vn1-cdn\.pgimgs\.com/[^"\s]+?\.(?:jpg|jpeg|png)', html)
    video_thumb = vt.group(0) if vt else ""

    gps = re.search(r"maps/embed/v1/place\?q=(-?[\d.]+),(-?[\d.]+)", html)
    gps_lat, gps_lng = (gps.group(1), gps.group(2)) if gps else (None, None)

    agent = re.search(r'(guru\.batdongsan\.com\.vn/pa/([0-9a-f]+)(\?[^"\s]+)?)', html)
    agent_url = agent_id = agent_params = agent_name = ""
    if agent:
        agent_url = "https://" + agent.group(1)
        agent_id = agent.group(2)
        agent_params = agent.group(3).replace("&amp;", "&") if agent.group(3) else ""
        agent_name = txt(r'class="re__contact-name[^"]*"[^>]*>(.*?)</a>')

    published = modified = category = ""
    for blk in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL):
        try:
            d = json.loads(blk)
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        if d.get("@type") == "RealEstateListing":
            published = d.get("@datePublished", "")
            modified = d.get("@dateModified", "")
        elif d.get("@type") == "BreadcrumbList":
            category = " > ".join(i.get("name", "") for i in d.get("itemListElement", []))

    description = txt(r'class="[^"]*descript[^"]*"[^>]*>(.*?)</div>')

    # location
    city_id = district_id = ward_id = street_id = None
    street_text = ""
    if resolver is not None:
        city_id, district_id, ward_id, street_id, street_text = resolver.resolve(address, city_hint)

    return {
        "url": url,
        "listing_id": listing_id,
        "title": txt(r"<h1[^>]*>(.*?)</h1>"),
        "price_text": price_text,
        "price_vnd": parse_price_vnd(price_text),
        "price_per_m2": parse_price_vnd(ppm_text),
        "area_text": area_text,
        "area_m2": normalize_float(area_text),
        "bedrooms": _spec_int(specs, ["phòng ngủ"]),
        "bathrooms": _spec_int(specs, ["phòng tắm", "phòng vệ sinh", "wc"]),
        "floors": _spec_int(specs, ["số tầng", "số lầu"]),
        "facade_m": normalize_float(specs.get("Mặt tiền", "")),
        "road_m": normalize_float(specs.get("Đường vào", "")),
        "direction": specs.get("Hướng nhà", ""),
        "balcony_dir": specs.get("Hướng ban công", ""),
        "legal_status": specs.get("Pháp lý", ""),
        "interior": specs.get("Nội thất", ""),
        "address_text": address,
        "street_text": street_text,
        "city_id": city_id,
        "district_id": district_id,
        "ward_id": ward_id,
        "street_id": street_id,
        "gps_lat": gps_lat,
        "gps_lng": gps_lng,
        "posted_at": posted,
        "expiry_at": expiry,
        "tier": tier,
        "agent_id": agent_id,
        "agent_name": agent_name,
        "agent_url": agent_url,
        "agent_params": agent_params,
        "published_at": published,
        "modified_at": modified,
        "description": description,
        "specs": specs,
        "images": images,
        "video": video,
        "video_thumb": video_thumb,
        "category": category,
    }


def _spec_int(specs, keys):
    for k, v in specs.items():
        if any(key in k.lower() for key in keys):
            m = re.search(r"(\d+)", v)
            return int(m.group(1)) if m else None
    return None


def match_category(con, url, cache=None):
    """Match category by URL first-segment prefix. cache = rows from SELECT id,slug,txn_type."""
    cats = cache if cache is not None else con.execute("SELECT id, slug, txn_type FROM categories").fetchall()
    m = re.search(r"batdongsan\.com\.vn/([^/]+)/", url)
    if not m:
        m = re.search(r"batdongsan\.com\.vn/([^/]+)$", url)
    seg = m.group(1) if m else ""
    best, best_id = None, None
    for r in cats:
        if r["slug"] and seg.startswith(r["slug"]) and (best is None or len(r["slug"]) > len(best)):
            best, best_id = r["slug"], r["id"]
    return best_id


class LocResolver:
    def __init__(self, con):
        self.con = con
        self.city_by_slugname = {slugify(r["name"]): r["id"] for r in con.execute("SELECT id, name FROM cities")}
        self.city_by_code = {r["code"]: r["id"] for r in con.execute("SELECT id, code FROM cities") if r["code"]}

    def _alias(self, old_name, old_type, old_parent):
        """Look up location_aliases: old -> new name (prefer matching old_parent)."""
        row = self.con.execute(
            "SELECT new_name, new_type, new_parent FROM location_aliases "
            "WHERE old_name=? AND old_type=? AND (old_parent=? OR old_parent IS NULL) "
            "ORDER BY (old_parent IS NOT NULL) DESC, id LIMIT 1",
            (old_name, old_type, old_parent or ""),
        ).fetchone()
        return row or None

    def log_unresolved(self, address_text, city_hint, reason):
        try:
            self.con.execute(
                "INSERT INTO unresolved_addresses (address_text, city_hint, reason) VALUES (?,?,?)",
                (address_text, city_hint, reason),
            )
        except Exception:
            pass

    def resolve(self, address_text, city_hint=None):
        if not address_text:
            return city_hint, None, None, None, ""
        parts = [p.strip() for p in address_text.split(",") if p.strip()]

        city_id = city_hint
        if city_hint is None or city_hint not in self.city_by_code.values():
            for p in reversed(parts):
                cid = self.city_by_slugname.get(slugify(p))
                if cid:
                    city_id = cid
                    parts.remove(p)
                    break

        ward_name = district_name = street_name = None
        for p in list(parts):
            pl = p.lower()
            if any(k in pl for k in ("phường", "xã", "thị trấn", "tt.")):
                ward_name = re.sub(r"^(phường|xã|thị trấn|tt\.?)\s*", "", p, flags=re.IGNORECASE).strip()
                parts.remove(p)
            elif any(k in pl for k in ("quận", "huyện", "thị xã", "tx.", "tp.")):
                district_name = re.sub(r"^(quận|huyện|thị xã|tx\.?|tp\.?)\s*", "", p, flags=re.IGNORECASE).strip()
                parts.remove(p)

        # NOTE: the district keeps the site's name (the site still uses old
        # district/ward names). Aliases are only used for a ward when it is not
        # found in the site hierarchy (units renamed after the mergers).

        if parts:
            first = parts[0]
            if any(k in first.lower() for k in ("đường", "đ.", "số", "số nhà")):
                street_name = re.sub(r"^(đường|đ\.?|số)\s*", "", first, flags=re.IGNORECASE).strip()
                parts.remove(first)
            else:
                street_name = first.strip()
                parts.remove(first)

        if city_id is None:
            self.log_unresolved(address_text, city_hint, "no_city")
            return None, None, None, None, ""

        district_id = ward_id = street_id = None
        if district_name:
            row = self.con.execute(
                "SELECT id FROM districts WHERE city_id=? AND name=?", (city_id, district_name)
            ).fetchone()
            if row:
                district_id = row["id"]
            else:
                cur = self.con.execute(
                    "INSERT INTO districts (city_id, name, slug) VALUES (?,?,?)",
                    (city_id, district_name, slugify(district_name)),
                )
                district_id = cur.lastrowid
        if ward_name:
            # 1) match by site name (by district, fallback by city when no district)
            if district_id:
                row = self.con.execute(
                    "SELECT id FROM wards WHERE district_id=? AND name=?",
                    (district_id, ward_name),
                ).fetchone()
            else:
                row = self.con.execute(
                    "SELECT id FROM wards WHERE city_id=? AND name=? ORDER BY id LIMIT 1",
                    (city_id, ward_name),
                ).fetchone()
            # 2) alias fallback: old unit -> current name (merger compatibility)
            if row is None:
                a = self._alias(ward_name, "ward", f"Quận {district_name}" if district_name else None)
                if a:
                    ward_name = a["new_name"]
                    if district_id:
                        row = self.con.execute(
                            "SELECT id FROM wards WHERE district_id=? AND name=?",
                            (district_id, ward_name),
                        ).fetchone()
                    else:
                        row = self.con.execute(
                            "SELECT id FROM wards WHERE city_id=? AND name=? ORDER BY id LIMIT 1",
                            (city_id, ward_name),
                        ).fetchone()
            if row:
                ward_id = row["id"]
            else:
                cur = self.con.execute(
                    "INSERT INTO wards (district_id, city_id, name, slug) VALUES (?,?,?,?)",
                    (district_id, city_id, ward_name, slugify(ward_name)),
                )
                ward_id = cur.lastrowid
        if street_name:
            row = self.con.execute(
                "SELECT id FROM streets WHERE city_id=? AND name=? ORDER BY id LIMIT 1", (city_id, street_name)
            ).fetchone()
            if row:
                street_id = row["id"]
            else:
                cur = self.con.execute(
                    "INSERT INTO streets (city_id, district_id, ward_id, name, slug) VALUES (?,?,?,?,?)",
                    (city_id, district_id, ward_id, street_name, slugify(street_name)),
                )
                street_id = cur.lastrowid
        return city_id, district_id, ward_id, street_id, street_name
