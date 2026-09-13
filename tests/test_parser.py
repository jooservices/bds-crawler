from parser import normalize_float, parse_price_vnd


def test_parse_price_vnd():
    assert parse_price_vnd("27 tỷ") == 27_000_000_000
    assert parse_price_vnd("1,15 tỷ") == 1_150_000_000
    assert parse_price_vnd("450 triệu") == 450_000_000
    assert parse_price_vnd("Giá thỏa thuận") is None
    assert parse_price_vnd("Thương lượng") is None
    assert parse_price_vnd("") is None


def test_parse_price_vnd_per_m2():
    # "450 triệu/m²" -> amount (per m2), but split on "/" first
    assert parse_price_vnd("450 triệu/m²") == 450_000_000


def test_normalize_float():
    assert normalize_float("60 m²") == 60.0
    assert normalize_float("117,5 m²") == 117.5
    assert normalize_float("5 m") == 5.0
    assert normalize_float("") is None
    assert normalize_float(None) is None
