import math
from dataclasses import dataclass, field

from risk_engine.exposure import check_exposure


@dataclass
class SymbolSpec:
    symbol: str
    tick_size: float
    tick_value: float      # nilai 1 tick per 1 lot, dalam USD
    volume_min: float
    volume_step: float
    volume_max: float
    margin_per_lot: float  # margin 1 lot, dalam USD


@dataclass
class TradeRequest:
    symbol: str
    direction: str         # "BUY" atau "SELL"
    entry: float
    stop: float
    spread_price: float    # spread dalam satuan harga


@dataclass
class RiskDecision:
    approved: bool = False
    symbol: str = ""
    direction: str = ""
    lot: float = 0.0
    entry: float = 0.0
    stop: float = 0.0
    stop_distance: float = 0.0
    risk_usd: float = 0.0
    margin_usd: float = 0.0
    reasons: list = field(default_factory=list)


def evaluate_trade(req, spec, cfg, capital, data_valid, open_positions, dd_monitor, kill_switch):
    d = RiskDecision(symbol=req.symbol, direction=req.direction, entry=req.entry)

    def reject(msg):
        d.approved = False
        d.reasons.append(msg)
        return d

    # 1. Kill-switch
    if kill_switch.is_active():
        return reject(f"KILL-SWITCH aktif: {kill_switch.reason()}")

    # 2. Data harus valid
    if not data_valid:
        return reject("Data tidak valid, trade ditolak")

    # 3. Drawdown
    st = dd_monitor.status(cfg)
    if st["total_breach"]:
        kill_switch.trigger(f"Drawdown {st['drawdown_pct']:.1f}% melewati batas {cfg['max_drawdown_pct']}%")
        return reject("Batas drawdown total terlewati, kill-switch diaktifkan")
    if st["daily_breach"]:
        return reject(f"Batas rugi sesi terlewati ({st['daily_loss_pct']:.1f}%)")

    # 4. Arah dan stop
    if req.direction not in ("BUY", "SELL"):
        return reject("Arah harus BUY atau SELL")
    stop = req.stop
    pct = cfg.get("stop_pct_of_price")
    if pct:
        stop = req.entry * (1 - pct / 100) if req.direction == "BUY" else req.entry * (1 + pct / 100)
    stop_distance = (req.entry - stop) if req.direction == "BUY" else (stop - req.entry)
    if stop_distance <= 0:
        return reject("Stop berada di sisi yang salah dari entry")
    d.stop = stop
    d.stop_distance = stop_distance

    # 5. Spread terhadap jarak stop
    if req.spread_price > cfg["max_spread_to_stop_ratio"] * stop_distance:
        return reject("Spread terlalu besar dibanding jarak stop")

    # 6. Ukuran lot dari risiko (skenario terburuk: stop + spread + komisi)
    loss_per_lot = stop_distance / spec.tick_size * spec.tick_value
    spread_per_lot = req.spread_price / spec.tick_size * spec.tick_value
    cost_per_lot = loss_per_lot + spread_per_lot + cfg["commission_per_lot_usd"]
    budget = capital * cfg["risk_per_trade_pct"] / 100
    raw_lot = budget / cost_per_lot
    lot = math.floor(raw_lot / spec.volume_step + 1e-9) * spec.volume_step
    lot = round(min(lot, spec.volume_max), 8)
    if lot < spec.volume_min - 1e-12:
        need = spec.volume_min * cost_per_lot
        return reject(f"Lot minimum {spec.volume_min} butuh risiko {need:.2f} USD, batas {budget:.2f} USD")
    d.lot = lot
    d.risk_usd = lot * cost_per_lot
    d.margin_usd = lot * spec.margin_per_lot

    # 7. Eksposur
    reasons = check_exposure(open_positions, req.symbol, d.risk_usd, d.margin_usd, capital, cfg)
    if reasons:
        d.reasons.extend(reasons)
        return d

    d.approved = True
    return d
