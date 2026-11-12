from dataclasses import dataclass, field
from datetime import datetime, timezone

REQUIRED = ["time_utc", "open", "high", "low", "close", "tick_volume", "spread"]
TF_MINUTES = {"M5": 5, "M15": 15, "H1": 60, "H4": 240}


@dataclass
class ValidationResult:
    valid: bool = True
    reasons: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def market_open(now_utc):
    """Perkiraan jam pasar forex buka (UTC). Tutup Jumat 21:00 sampai Minggu 22:00."""
    wd = now_utc.weekday()
    if wd == 5:
        return False
    if wd == 4 and now_utc.hour >= 21:
        return False
    if wd == 6 and now_utc.hour < 22:
        return False
    return True


def validate_candles(df, tf="M15", now=None, max_gap_minutes=120):
    res = ValidationResult()
    now = now or datetime.now(timezone.utc)

    def fail(msg):
        res.valid = False
        res.reasons.append(msg)

    # 1. Kosong / kolom kurang
    if df is None or len(df) == 0:
        fail("DataFrame kosong")
        return res
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        fail(f"Kolom hilang: {missing}")
        return res

    # 2. Nilai kosong
    if df[REQUIRED].isnull().any().any():
        fail("Ada nilai kosong (NaN)")
        return res

    # 3. Timestamp
    t = df["time_utc"]
    if t.duplicated().any():
        fail("Timestamp duplikat")
    if not t.is_monotonic_increasing:
        fail("Timestamp tidak urut naik")

    # 4. Harga masuk akal
    if (df[["open", "high", "low", "close"]] <= 0).any().any():
        fail("Ada harga <= 0")
    if (df["high"] < df["low"]).any():
        fail("Ada candle high < low")
    bad_body = (
        (df["open"] > df["high"]) | (df["open"] < df["low"])
        | (df["close"] > df["high"]) | (df["close"] < df["low"])
    )
    if bad_body.any():
        fail("Ada open/close di luar rentang high-low")
    if (df["spread"] < 0).any():
        fail("Ada spread negatif")

    # 5. Gap candle (weekend dilewatin)
    step = TF_MINUTES[tf]
    diffs = t.diff().dt.total_seconds() / 60
    bad_gaps = []
    for i in df.index[diffs > step]:
        prev, cur = t[i - 1], t[i]
        if prev.weekday() in (4, 5) and cur.weekday() in (6, 0):
            continue
        gap = diffs[i]
        if gap <= max_gap_minutes:
            res.warnings.append(f"Gap {gap:.0f} menit: {prev} -> {cur}")
        else:
            bad_gaps.append(f"{gap:.0f} menit: {prev} -> {cur}")
    if bad_gaps:
        fail(f"Gap tengah minggu {len(bad_gaps)}x, contoh {bad_gaps[0]}")

    # 6. Stale dan timestamp masa depan
    now_naive = now.replace(tzinfo=None)
    age = (now_naive - t.iloc[-1]).total_seconds() / 60
    if age < -5:
        fail("Candle terakhir ada di masa depan")
    elif market_open(now) and age > 2 * step:
        fail(f"Data stale: candle terakhir {age:.0f} menit lalu")

    # 7. Spread anomali (warning saja, keputusan akhir ada di RISK)
    med = df["spread"].median()
    if med > 0 and df["spread"].iloc[-1] > 5 * med:
        res.warnings.append(f"Spread loncat: {df['spread'].iloc[-1]} vs median {med}")

    return res
