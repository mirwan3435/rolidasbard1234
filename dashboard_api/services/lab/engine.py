"""Mesin backtest Lab.

Aturan yang diuji:
- entry di open bar berikutnya (tanpa look-ahead)
- SL dan TP di bar yang sama dianggap SL duluan
- biaya selalu dipotong
"""
import math


def _point_value(spec):
    tick = float(spec["tick_size"])
    if tick <= 0:
        return 0.0
    return float(spec["tick_value"]) / tick


def _lot(equity, risk_pct, loss_per_lot, spec, skip_pct):
    if loss_per_lot <= 0 or equity <= 0:
        return 0.0, "skip"
    budget = equity * risk_pct / 100
    step = float(spec["volume_step"])
    vmin = float(spec["volume_min"])
    vmax = float(spec["volume_max"])
    raw = budget / loss_per_lot
    lot = math.floor(raw / step + 1e-9) * step
    lot = min(lot, vmax)
    if lot < vmin - 1e-12:
        need_pct = (vmin * loss_per_lot) / equity * 100
        if skip_pct is not None and need_pct > float(skip_pct):
            return 0.0, "skip"
        return 0.0, "skip"
    return round(lot, 8), "ok"


def _resolve(direction, bar, sl, tp):
    if direction == "buy":
        hit_sl = bar["low"] <= sl
        hit_tp = bar["high"] >= tp
    else:
        hit_sl = bar["high"] >= sl
        hit_tp = bar["low"] <= tp
    if hit_sl:
        return sl, "sl"
    if hit_tp:
        return tp, "tp"
    return None, None


def run_backtest(bars, detect, params, spec, equity, risk_pct, commission_per_lot, skip_pct, slippage_points=0):
    params = params or {}
    trades = []
    equity_curve = [{"i": 0, "equity": equity}]
    cash = float(equity)
    point_value = _point_value(spec)
    spread = float(spec.get("spread") or 0)
    slip = float(slippage_points) * float(spec["tick_size"])
    i = 0
    while i < len(bars) - 1:
        window = bars[: i + 1]
        signal = detect(window, params)
        if not signal:
            i += 1
            continue
        entry_bar = bars[i + 1]
        entry = float(entry_bar["open"])
        direction = signal["direction"]
        sl_dist = float(signal["sl_distance"])
        tp_dist = float(signal["tp_distance"])
        if direction == "buy":
            sl = entry - sl_dist
            tp = entry + tp_dist
        else:
            sl = entry + sl_dist
            tp = entry - tp_dist
        loss_per_lot = (sl_dist + spread + slip) * point_value + float(commission_per_lot)
        lot, status = _lot(cash, risk_pct, loss_per_lot, spec, skip_pct)
        if status != "ok":
            i += 1
            continue
        exit_price = None
        exit_reason = "open"
        exit_index = len(bars) - 1
        for j in range(i + 1, len(bars)):
            price, reason = _resolve(direction, bars[j], sl, tp)
            if price is not None:
                exit_price = price
                exit_reason = reason
                exit_index = j
                break
        if exit_price is None:
            exit_price = float(bars[-1]["close"])
            exit_reason = "eod"
        sign = 1 if direction == "buy" else -1
        gross = (exit_price - entry) * sign * point_value * lot
        cost = (spread + slip) * point_value * lot + float(commission_per_lot) * lot
        net = gross - cost
        risk_cash = sl_dist * point_value * lot
        r_multiple = (net / risk_cash) if risk_cash else 0
        cash += net
        trades.append({
            "entry_index": i + 1,
            "exit_index": exit_index,
            "entry": entry,
            "exit": exit_price,
            "direction": direction,
            "lot": lot,
            "result_usd": round(net, 4),
            "cost_usd": round(cost, 4),
            "r_multiple": round(r_multiple, 4),
            "reason": exit_reason,
            "source": "real",
        })
        equity_curve.append({"i": exit_index, "equity": round(cash, 4)})
        i = exit_index + 1
    return {"trades": trades, "equity_curve": equity_curve, "ending_equity": round(cash, 4)}


def kpis(result):
    trades = result["trades"]
    wins = [t for t in trades if t["result_usd"] > 0]
    losses = [t for t in trades if t["result_usd"] <= 0]
    rs = [t["r_multiple"] for t in trades]
    gross_win = sum(t["result_usd"] for t in wins)
    gross_loss = abs(sum(t["result_usd"] for t in losses))
    peak = None
    max_dd = 0.0
    for point in result["equity_curve"]:
        value = point["equity"]
        peak = value if peak is None else max(peak, value)
        if peak:
            max_dd = max(max_dd, (peak - value) / peak * 100)
    count = len(trades)
    return {
        "trade_count": count,
        "win_rate": (len(wins) / count * 100) if count else 0,
        "avg_r": (sum(rs) / len(rs)) if rs else 0,
        "avg_win": (gross_win / len(wins)) if wins else 0,
        "avg_loss": (sum(t["result_usd"] for t in losses) / len(losses)) if losses else 0,
        "expectancy_r": (sum(rs) / len(rs)) if rs else 0,
        "expectancy_usd": (sum(t["result_usd"] for t in trades) / count) if count else 0,
        "profit_factor": (gross_win / gross_loss) if gross_loss else None,
        "max_drawdown_pct": max_dd,
        "net_usd": sum(t["result_usd"] for t in trades),
    }
