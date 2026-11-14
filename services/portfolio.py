"""PORTFOLIO: keranjang korelasi. Menolak kandidat, tidak mengirim order."""
GROUPS = {
    "XAUUSD": "metals",
    "XAGUSD": "metals",
    "EURUSD": "usd",
    "USDJPY": "usd",
    "USOIL": "energy",
    "USTEC": "index",
    "DXY": "context",
}


def canonical(symbol: str):
    name = symbol.upper().replace(" ", "")
    for suffix in ("_X100M", "USDM", "M"):
        if name.endswith(suffix) and name[: -len(suffix)] in GROUPS:
            return name[: -len(suffix)]
    return name


def allow(symbol: str, open_symbols, heat_pct: float, heat_limit: float):
    if canonical(symbol) == "DXY":
        return False, "DXY hanya konteks"
    if heat_pct >= heat_limit:
        return False, "Panas portofolio penuh"
    group = GROUPS.get(canonical(symbol))
    if group and any(GROUPS.get(canonical(other)) == group for other in open_symbols):
        return False, "Keranjang korelasi sudah terisi"
    return True, "Lolos saringan portofolio"
