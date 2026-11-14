"""Kartu konsep. Umpan balik disimpan, tidak mengubah RISK."""
import json
from datetime import datetime, timezone

from dashboard_api.paths import DATA, ensure_dirs

SEEDS = [
    ("range", "Range", "structure", "Harga bergerak di antara dua sisi sampai ada penutupan di luarnya."),
    ("bos", "BOS", "structure", "Break of structure: penutupan melewati swing searah bias."),
    ("choch", "CHOCH", "structure", "Change of character: swing berlawanan yang menandai pergeseran."),
    ("order_block", "Order block", "price_action", "Candle terakhir sebelum perpindahan yang kemudian diuji kembali."),
    ("fvg", "FVG", "price_action", "Celah tiga candle. Bukan jaminan harga kembali."),
    ("liquidity_sweep", "Liquidity sweep", "ict", "Harga menyapu high/low lalu menolak."),
    ("crt", "CRT", "ict", "Candle referensi di-sweep, lalu close kembali ke dalam range."),
    ("snd", "Supply / demand", "price_action", "RBR, DBD, DBR, RBD. Zona fresh hanya sentuhan pertama."),
    ("sbr_rbs", "SBR / RBS", "price_action", "Support yang jebol menjadi resistance, atau sebaliknya."),
    ("breakout", "Breakout", "price_action", "Body candle menutup di luar range, bukan hanya sumbu."),
    ("orderflow_proxy", "Order-flow proxy", "flow", "Delta tick dan volume hanya konteks, bukan sinyal entry."),
    ("power_of_3", "Power of 3", "ict", "Akumulasi, manipulasi, lalu distribusi. Hipotesis, bukan fakta."),
]


def _cards_dir():
    folder = DATA / "knowledge" / "cards"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def ensure_cards():
    ensure_dirs()
    folder = _cards_dir()
    for cid, title, category, plain in SEEDS:
        path = folder / f"{cid}.json"
        if path.exists():
            continue
        doc = {
            "id": cid,
            "title": title,
            "category": category,
            "plain_language": plain,
            "code_snippet": f"# sample\n# {cid}: belum ada plugin produksi",
            "example_candles": [],
            "found_count": None,
            "status": "unchecked",
            "source": "sample",
        }
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")


_CANDLE = [
    {"o": 10, "h": 11, "l": 9.6, "c": 10.8},
    {"o": 10.8, "h": 11.4, "l": 10.5, "c": 11.2},
    {"o": 11.2, "h": 11.3, "l": 10.4, "c": 10.6},
    {"o": 10.6, "h": 10.9, "l": 10.2, "c": 10.3},
    {"o": 10.3, "h": 11.6, "l": 10.1, "c": 11.4},
    {"o": 11.4, "h": 11.8, "l": 11.1, "c": 11.6},
]


def cards():
    ensure_cards()
    from strategies.common import snippet_for
    rows = []
    for path in sorted(_cards_dir().glob("*.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not row.get("example_candles"):
            row["example_candles"] = _CANDLE
        code = snippet_for(row.get("id") or "")
        if code:
            row["code_snippet"] = code
            row["code_origin"] = "real"
        else:
            row["code_origin"] = "sample"
        if row.get("found_count") is None:
            row["source"] = "sample"
        rows.append(row)
    return rows


def verdict(card_id: str, verdict_value: str, note: str):
    if verdict_value not in {"ok", "not_ok"}:
        raise ValueError("Verdict harus ok atau not_ok")
    ensure_cards()
    path = _cards_dir() / f"{card_id}.json"
    if not path.is_file():
        raise KeyError(card_id)
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["status"] = verdict_value
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    row = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "id": card_id,
        "verdict": verdict_value,
        "note": (note or "")[:500],
    }
    feedback = DATA / "knowledge" / "feedback.jsonl"
    with feedback.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def review():
    return [card for card in cards() if card.get("status") == "not_ok"]
