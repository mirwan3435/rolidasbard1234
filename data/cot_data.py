import time
from datetime import datetime, timedelta, timezone

import requests

HEADERS = {"User-Agent": "PythonAILab-COT-Research/1.0 (personal research)"}
URL = "https://publicreporting.cftc.gov/resource/{}.json"
MAX_AGE_DAYS = 11  # posisi Selasa, rilis Jumat: umur normal 3-10 hari

# pair_sign: +1 kalau futures searah pair, -1 kalau kebalik (yen vs USDJPY)
COT_MAP = {
    "EURUSD": {
        "dataset": "gpe5-46if",
        "market": "EURO FX - CHICAGO MERCANTILE EXCHANGE",
        "pair_sign": 1,
        "groups": {
            "lev_money": ("lev_money_positions_long", "lev_money_positions_short"),
            "asset_mgr": ("asset_mgr_positions_long", "asset_mgr_positions_short"),
            "dealer": ("dealer_positions_long_all", "dealer_positions_short_all"),
        },
    },
    "USDJPY": {
        "dataset": "gpe5-46if",
        "market": "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE",
        "pair_sign": -1,
        "groups": {
            "lev_money": ("lev_money_positions_long", "lev_money_positions_short"),
            "asset_mgr": ("asset_mgr_positions_long", "asset_mgr_positions_short"),
            "dealer": ("dealer_positions_long_all", "dealer_positions_short_all"),
        },
    },
    "XAUUSD": {
        "dataset": "72hh-3qpy",
        "market": "GOLD - COMMODITY EXCHANGE INC.",
        "pair_sign": 1,
        "groups": {
            "managed_money": ("m_money_positions_long_all", "m_money_positions_short_all"),
        },
    },
}


def _fetch(dataset, market, limit=8, retries=3):
    params = {
        "$where": f"market_and_exchange_names = '{market}'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": limit,
    }
    last_err = None
    for _ in range(retries):
        try:
            r = requests.get(URL.format(dataset), params=params, headers=HEADERS, timeout=90)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_err = e
            time.sleep(5)
    raise RuntimeError(f"Gagal tarik COT {market}: {last_err}")


def _parse_date(s):
    return datetime.strptime(s[:10], "%Y-%m-%d").date()


def get_cot(symbol, now=None):
    """Positioning mingguan. Konteks bias mingguan, BUKAN sinyal real-time."""
    cfg = COT_MAP[symbol]
    now = now or datetime.now(timezone.utc)
    out = {
        "symbol": symbol,
        "market": cfg["market"],
        "valid": True,
        "reasons": [],
        "warnings": [],
        "groups": {},
    }

    def fail(msg):
        out["valid"] = False
        out["reasons"].append(msg)

    try:
        rows = _fetch(cfg["dataset"], cfg["market"])
    except RuntimeError as e:
        fail(str(e))
        return out

    if len(rows) < 2:
        fail("Data COT kurang dari 2 minggu")
        return out
    if rows[0].get("market_and_exchange_names") != cfg["market"]:
        fail("Nama pasar tidak cocok persis")
        return out

    latest, prev = rows[0], rows[1]
    report_date = _parse_date(latest["report_date_as_yyyy_mm_dd"])
    prev_date = _parse_date(prev["report_date_as_yyyy_mm_dd"])
    age = (now.date() - report_date).days

    out["report_date"] = report_date.isoformat()
    out["release_date_est"] = (report_date + timedelta(days=3)).isoformat()
    out["age_days"] = age

    if age > MAX_AGE_DAYS:
        fail(f"COT basi: posisi {report_date}, umur {age} hari")
    if age < 0:
        fail("Tanggal laporan di masa depan")
    if (report_date - prev_date).days != 7:
        out["warnings"].append(f"Jarak minggu tidak 7 hari: {prev_date} -> {report_date}")

    sign = cfg["pair_sign"]
    for name, (lc, sc) in cfg["groups"].items():
        try:
            long_, short_ = int(latest[lc]), int(latest[sc])
            net = long_ - short_
            prev_net = int(prev[lc]) - int(prev[sc])
        except (KeyError, ValueError, TypeError) as e:
            fail(f"Kolom {name} bermasalah: {e}")
            continue
        out["groups"][name] = {
            "long": long_,
            "short": short_,
            "net": net,
            "net_pair": sign * net,
            "change_net_pair": sign * (net - prev_net),
        }

    return out
