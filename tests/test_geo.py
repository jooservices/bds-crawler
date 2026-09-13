import sqlite3

from parser import LocResolver, slugify


def make_db():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    with open("schema.sql") as f:
        con.executescript(f.read())
    con.execute("INSERT INTO cities (id, code, name, slug) VALUES (1,'HN','Hà Nội','ha-noi')")
    con.execute("INSERT INTO cities (id, code, name, slug) VALUES (2,'HCM','Hồ Chí Minh','tp-hcm')")
    con.execute("INSERT INTO cities (id, code, name, slug) VALUES (3,'DDN','Đà Nẵng','da-nang')")
    con.execute("INSERT INTO districts (id, city_id, name, slug) VALUES (1,2,'Củ Chi','cu-chi')")
    con.execute("INSERT INTO wards (id, district_id, city_id, name) VALUES (1,1,2,'Tân An Hội')")
    con.commit()
    return con


def test_slugify():
    assert slugify("Hồ Chí Minh") == "ho-chi-minh"
    assert slugify("Đà Nẵng") == "da-nang"
    assert slugify("Bà Rịa - Vũng Tàu") == "ba-ria-vung-tau"


def test_resolve_street_ward_district_city():
    con = make_db()
    r = LocResolver(con)
    city, dist, ward, _, stext = r.resolve("Đường Nguyễn Văn Khạ, Xã Tân An Hội, Huyện Củ Chi, Hồ Chí Minh")
    assert city == 2
    assert dist == 1
    assert ward == 1
    assert stext == "Nguyễn Văn Khạ"


def test_resolve_creates_missing_district():
    con = make_db()
    r = LocResolver(con)
    city, dist, _, _, _ = r.resolve("Phường Tây Mỗ, Quận Nam Từ Liêm, Hà Nội")
    assert city == 1
    d = con.execute("SELECT name FROM districts WHERE id=?", (dist,)).fetchone()
    assert d["name"] == "Nam Từ Liêm"


def test_resolve_alias_renamed_ward():
    con = make_db()
    con.execute(
        "INSERT INTO location_aliases (old_name, old_type, old_parent, new_name, new_type, new_parent, note, source) "
        "VALUES ('6','ward','Quận 3','Xuân Hòa','ward','TP.HCM','sap nhap','NQ1685')"
    )
    con.commit()
    r = LocResolver(con)
    city, _, ward, _, _ = r.resolve("17C Hai Bà Trưng, Phường 6, Quận 3, Hồ Chí Minh")
    assert city == 2
    w = con.execute("SELECT name FROM wards WHERE id=?", (ward,)).fetchone()
    assert w["name"] == "Xuân Hòa"


def test_resolve_unresolved_logged():
    con = make_db()
    r = LocResolver(con)
    city, *_ = r.resolve("Khu công nghiệp không tên, Huyện Xa Xôi, Tỉnh Không Rõ")
    assert city is None
    assert con.execute("SELECT COUNT(*) FROM unresolved_addresses").fetchone()[0] == 1
