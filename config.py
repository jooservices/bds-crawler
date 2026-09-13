"""JOOservices batdongsan crawler - config."""
import os
from pathlib import Path

BASE = Path(__file__).parent

# Browser / CDP (env override cho Docker)
CHROME = os.environ.get("BDS_CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
PROFILE = Path(os.environ.get("BDS_PROFILE", "/tmp/bds-crawl-current"))
PORT = int(os.environ.get("BDS_PORT", "9241"))
WARMUP = "https://batdongsan.com.vn/nha-dat-ban-ha-noi"

# DB
DB = Path(os.environ.get("BDS_DB", str(BASE / "bds.db")))
SCHEMA = BASE / "schema.sql"

# Concurrency & throttle
TABS = 5
MIN_INTERVAL = 1.0          # giây tối thiểu giữa 2 request (pool)
MAX_REQ_PER_MIN = 40        # trần request/phút
MAX_ATTEMPTS = 5            # max attempts per URL
CHALLENGE_WAIT = 45         # giây chờ clearance tại chỗ

# Delta
DELTA_INTERVAL = 6 * 3600   # 6h, re-crawl tin active

# Logging
LOG_DIR = BASE / "logs"
LOG_FILE = LOG_DIR / "crawler.log"

# 63 tỉnh/thành (code site, name, slug site)
# official_code: legacy GSO code (01=HN, 79=HCM, 48=DN...)
CITIES = [
    ("HN",  "Hà Nội",            "ha-noi",            "01"),
    ("HCM", "Hồ Chí Minh",       "tp-hcm",            "79"),
    ("DDN", "Đà Nẵng",           "da-nang",           "48"),
    ("HPG", "Hải Phòng",         "hai-phong",         "31"),
    ("CTH", "Cần Thơ",           "can-tho",           "92"),
    ("",    "An Giang",          "an-giang",          "89"),
    ("",    "Bà Rịa - Vũng Tàu", "ba-ria-vung-tau",   "77"),
    ("",    "Bắc Giang",         "bac-giang",         "24"),
    ("",    "Bắc Kạn",           "bac-kan",           "06"),
    ("",    "Bạc Liêu",          "bac-lieu",          "95"),
    ("",    "Bắc Ninh",          "bac-ninh",          "22"),
    ("",    "Bến Tre",           "ben-tre",           "83"),
    ("",    "Bình Định",         "binh-dinh",         "52"),
    ("",    "Bình Dương",        "binh-duong",        "74"),
    ("",    "Bình Phước",        "binh-phuoc",        "70"),
    ("",    "Bình Thuận",        "binh-thuan",        "60"),
    ("",    "Cà Mau",            "ca-mau",            "96"),
    ("",    "Cao Bằng",          "cao-bang",          "04"),
    ("",    "Đắk Lắk",           "dak-lak",           "66"),
    ("",    "Đắk Nông",          "dak-nong",          "67"),
    ("",    "Điện Biên",         "dien-bien",         "11"),
    ("",    "Đồng Nai",          "dong-nai",          "75"),
    ("",    "Đồng Tháp",         "dong-thap",         "87"),
    ("",    "Gia Lai",           "gia-lai",           "64"),
    ("",    "Hà Giang",          "ha-giang",          "02"),
    ("",    "Hà Nam",            "ha-nam",            "35"),
    ("",    "Hà Tĩnh",           "ha-tinh",           "42"),
    ("",    "Hải Dương",         "hai-duong",         "30"),
    ("",    "Hậu Giang",         "hau-giang",         "93"),
    ("",    "Hòa Bình",          "hoa-binh",          "17"),
    ("",    "Hưng Yên",          "hung-yen",          "33"),
    ("",    "Khánh Hòa",         "khanh-hoa",         "56"),
    ("",    "Kiên Giang",        "kien-giang",        "91"),
    ("",    "Kon Tum",           "kon-tum",           "62"),
    ("",    "Lai Châu",          "lai-chau",          "12"),
    ("",    "Lâm Đồng",          "lam-dong",          "68"),
    ("",    "Lạng Sơn",          "lang-son",          "20"),
    ("",    "Lào Cai",           "lao-cai",           "10"),
    ("",    "Long An",           "long-an",           "80"),
    ("",    "Nam Định",          "nam-dinh",          "36"),
    ("",    "Nghệ An",           "nghe-an",           "40"),
    ("",    "Ninh Bình",         "ninh-binh",         "37"),
    ("",    "Ninh Thuận",        "ninh-thuan",        "58"),
    ("",    "Phú Thọ",           "phu-tho",           "25"),
    ("",    "Phú Yên",           "phu-yen",           "54"),
    ("",    "Quảng Bình",        "quang-binh",        "44"),
    ("",    "Quảng Nam",         "quang-nam",         "49"),
    ("",    "Quảng Ngãi",        "quang-ngai",        "51"),
    ("",    "Quảng Ninh",        "quang-ninh",        "22"),
    ("",    "Quảng Trị",         "quang-tri",         "45"),
    ("",    "Sóc Trăng",         "soc-trang",         "94"),
    ("",    "Sơn La",            "son-la",            "14"),
    ("",    "Tây Ninh",          "tay-ninh",          "72"),
    ("",    "Thái Bình",         "thai-binh",         "34"),
    ("",    "Thái Nguyên",       "thai-nguyen",       "19"),
    ("",    "Thanh Hóa",         "thanh-hoa",         "38"),
    ("",    "Thừa Thiên Huế",    "thua-thien-hue",    "46"),
    ("",    "Tiền Giang",        "tien-giang",        "82"),
    ("",    "Trà Vinh",          "tra-vinh",          "84"),
    ("",    "Tuyên Quang",       "tuyen-quang",       "08"),
    ("",    "Vĩnh Long",         "vinh-long",         "86"),
    ("",    "Vĩnh Phúc",         "vinh-phuc",         "26"),
    ("",    "Yên Bái",           "yen-bai",           "15"),
]

# Admin-unit aliases: old -> new (seeded from National Assembly resolutions)
# old_name/new_name use BARE names (no "Phường " prefix) to match the parser
# (old_name, old_type, old_parent, new_name, new_type, new_parent, note, source)
LOCATION_ALIASES = [
    # HCM - District 3 (2020: wards 6+7+8 -> Võ Thị Sáu; 2025: Võ Thị Sáu + P4 -> Xuân Hòa)
    ("6", "ward", "Quận 3", "Xuân Hòa", "ward", "TP.HCM", "6+7+8->Võ Thị Sáu(2020)->Xuân Hòa(2025)", "NQ1111/NQ1685"),
    ("7", "ward", "Quận 3", "Xuân Hòa", "ward", "TP.HCM", "6+7+8->Võ Thị Sáu(2020)->Xuân Hòa(2025)", "NQ1111/NQ1685"),
    ("8", "ward", "Quận 3", "Xuân Hòa", "ward", "TP.HCM", "6+7+8->Võ Thị Sáu(2020)->Xuân Hòa(2025)", "NQ1111/NQ1685"),
    ("Võ Thị Sáu", "ward", "Quận 3", "Xuân Hòa", "ward", "TP.HCM", "Võ Thị Sáu+P4->Xuân Hòa(2025)", "NQ1685"),
    ("1", "ward", "Quận 3", "Bàn Cờ", "ward", "TP.HCM", "1+2+3+5+part P4->Bàn Cờ(2025)", "NQ1685"),
    ("2", "ward", "Quận 3", "Bàn Cờ", "ward", "TP.HCM", "1+2+3+5+part P4->Bàn Cờ(2025)", "NQ1685"),
    ("3", "ward", "Quận 3", "Bàn Cờ", "ward", "TP.HCM", "1+2+3+5+part P4->Bàn Cờ(2025)", "NQ1685"),
    ("5", "ward", "Quận 3", "Bàn Cờ", "ward", "TP.HCM", "1+2+3+5+part P4->Bàn Cờ(2025)", "NQ1685"),
    ("9", "ward", "Quận 3", "Nhiêu Lộc", "ward", "TP.HCM", "9+11+12+14->Nhiêu Lộc(2025)", "NQ1685"),
    ("11", "ward", "Quận 3", "Nhiêu Lộc", "ward", "TP.HCM", "9+11+12+14->Nhiêu Lộc(2025)", "NQ1685"),
    ("12", "ward", "Quận 3", "Nhiêu Lộc", "ward", "TP.HCM", "9+11+12+14->Nhiêu Lộc(2025)", "NQ1685"),
    ("14", "ward", "Quận 3", "Nhiêu Lộc", "ward", "TP.HCM", "9+11+12+14->Nhiêu Lộc(2025)", "NQ1685"),
    ("Quận 3", "district", "Hồ Chí Minh", "Xuân Hòa", "ward", "TP.HCM", "district level abolished 1/7/2025", "NQ1685"),
    # Hanoi - Cầu Giấy district (NQ1656)
    ("Dịch Vọng", "ward", "Quận Cầu Giấy", "Cầu Giấy", "ward", "Hà Nội", "6 wards->Cầu Giấy(2025)", "NQ1656"),
    ("Dịch Vọng Hậu", "ward", "Quận Cầu Giấy", "Cầu Giấy", "ward", "Hà Nội", "6 wards->Cầu Giấy(2025)", "NQ1656"),
    ("Quan Hoa", "ward", "Quận Cầu Giấy", "Cầu Giấy", "ward", "Hà Nội", "6 wards->Cầu Giấy(2025)", "NQ1656"),
    ("Mỹ Đình 1", "ward", "Quận Cầu Giấy", "Cầu Giấy", "ward", "Hà Nội", "6 wards->Cầu Giấy(2025)", "NQ1656"),
    ("Mỹ Đình 2", "ward", "Quận Cầu Giấy", "Cầu Giấy", "ward", "Hà Nội", "6 wards->Cầu Giấy(2025)", "NQ1656"),
    ("Yên Hòa", "ward", "Quận Cầu Giấy", "Cầu Giấy", "ward", "Hà Nội", "6 wards->Cầu Giấy(2025)", "NQ1656"),
    ("Nghĩa Tân", "ward", "Quận Cầu Giấy", "Nghĩa Đô", "ward", "Hà Nội", "->Nghĩa Đô(2025)", "NQ1656"),
    ("Mễ Trì", "ward", "Quận Cầu Giấy", "Yên Hòa", "ward", "Hà Nội", "->Yên Hòa(2025)", "NQ1656"),
    ("Nhân Chính", "ward", "Quận Cầu Giấy", "Yên Hòa", "ward", "Hà Nội", "->Yên Hòa(2025)", "NQ1656"),
    ("Trung Hòa", "ward", "Quận Cầu Giấy", "Yên Hòa", "ward", "Hà Nội", "->Yên Hòa(2025)", "NQ1656"),
    ("Quận Cầu Giấy", "district", "Hà Nội", "Cầu Giấy", "ward", "Hà Nội", "district level abolished 1/7/2025", "NQ1656"),
]

# Category: slug -> (name, transaction, parent_slug)
CATEGORIES = {
    "nha-dat-ban":               ("Nhà đất bán",               "ban",       None),
    "ban-can-ho-chung-cu":       ("Bán căn hộ chung cư",      "ban",       "nha-dat-ban"),
    "ban-nha-rieng":             ("Bán nhà riêng",             "ban",       "nha-dat-ban"),
    "ban-nha-biet-thu-lien-ke":  ("Bán nhà biệt thự, liền kề", "ban",       "nha-dat-ban"),
    "ban-dat":                   ("Bán đất",                   "ban",       "nha-dat-ban"),
    "ban-dat-nen-du-an":         ("Bán đất nền dự án",         "ban",       "nha-dat-ban"),
    "ban-mat-tien-pho":          ("Bán mặt tiền phố",          "ban",       "nha-dat-ban"),
    "ban-van-phong":             ("Bán văn phòng",             "ban",       "nha-dat-ban"),
    "ban-kho-nha-xuong":         ("Bán kho, nhà xưởng",        "ban",       "nha-dat-ban"),
    "ban-phong-tro-nha-tro":     ("Bán phòng trọ, nhà trọ",    "ban",       "nha-dat-ban"),
    "ban-trang-trai-khu-nghi-duong": ("Bán trang trại, khu nghỉ dưỡng", "ban", "nha-dat-ban"),
    "ban-condotel":              ("Bán condotel",              "ban",       "nha-dat-ban"),
    "ban-loai-bat-dong-san-khac":("Bán loại BĐS khác",         "ban",       "nha-dat-ban"),

    "nha-dat-cho-thue":               ("Nhà đất cho thuê",       "cho-thue", None),
    "cho-thue-can-ho-chung-cu":       ("Cho thuê căn hộ chung cư", "cho-thue", "nha-dat-cho-thue"),
    "cho-thue-nha-rieng":             ("Cho thuê nhà riêng",       "cho-thue", "nha-dat-cho-thue"),
    "cho-thue-nha-biet-thu-lien-ke":  ("Cho thuê nhà biệt thự, liền kề", "cho-thue", "nha-dat-cho-thue"),
    "cho-thue-dat":                   ("Cho thuê đất",             "cho-thue", "nha-dat-cho-thue"),
    "cho-thue-mat-tien-pho":          ("Cho thuê mặt tiền phố",    "cho-thue", "nha-dat-cho-thue"),
    "cho-thue-van-phong":             ("Cho thuê văn phòng",       "cho-thue", "nha-dat-cho-thue"),
    "cho-thue-kho-nha-xuong":         ("Cho thuê kho, nhà xưởng",  "cho-thue", "nha-dat-cho-thue"),
    "cho-thue-phong-tro-nha-tro":     ("Cho thuê phòng trọ, nhà trọ", "cho-thue", "nha-dat-cho-thue"),
    "cho-thue-trang-trai-khu-nghi-duong": ("Cho thuê trang trại, khu nghỉ dưỡng", "cho-thue", "nha-dat-cho-thue"),
    "cho-thue-condotel":              ("Cho thuê condotel",        "cho-thue", "nha-dat-cho-thue"),
    "cho-thue-loai-bat-dong-san-khac":("Cho thuê loại BĐS khác",   "cho-thue", "nha-dat-cho-thue"),
}