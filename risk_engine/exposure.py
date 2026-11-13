def check_exposure(open_positions, new_symbol, new_risk_usd, new_margin_usd, capital, cfg):
    """Kembalikan daftar alasan penolakan (kosong = lolos)."""
    reasons = []
    if len(open_positions) >= cfg["max_open_positions"]:
        reasons.append(f"Posisi terbuka sudah {len(open_positions)} (maks {cfg['max_open_positions']})")
    if any(p["symbol"] == new_symbol for p in open_positions):
        reasons.append(f"Sudah ada posisi terbuka di {new_symbol}")
    total_risk = sum(p["risk_usd"] for p in open_positions) + new_risk_usd
    risk_limit = capital * cfg["max_total_risk_pct"] / 100
    if total_risk > risk_limit + 1e-9:
        reasons.append(f"Total risiko {total_risk:.2f} melebihi batas {risk_limit:.2f}")
    total_margin = sum(p.get("margin_usd", 0.0) for p in open_positions) + new_margin_usd
    margin_limit = capital * cfg["max_margin_pct"] / 100
    if total_margin > margin_limit + 1e-9:
        reasons.append(f"Total margin {total_margin:.2f} melebihi batas {margin_limit:.2f}")
    return reasons
