import os
from config import PROFILES, VIRTUAL_CAPITAL
from risk_engine.validation import SymbolSpec, TradeRequest, evaluate_trade
from risk_engine.drawdown import DrawdownMonitor
from risk_engine.kill_switch import KillSwitch

LOCK = os.path.join("logs", "test_kill.lock")
if os.path.exists(LOCK):
    os.remove(LOCK)

std = PROFILES["standard"]
exp = PROFILES["experiment_a"]
cap = VIRTUAL_CAPITAL

eur = SymbolSpec("EURUSD", 1e-5, 1.0, 0.01, 0.01, 200.0, 55.0)
xau = SymbolSpec("XAUUSD", 0.001, 0.1, 0.01, 0.01, 200.0, 195.0)
jpy = SymbolSpec("USDJPY", 0.001, 0.6253, 0.01, 0.01, 300.0, 50.0)


def run(req, spec, cfg=std, valid=True, open_pos=None, dd=None, ks=None):
    return evaluate_trade(req, spec, cfg, cap, valid, open_pos or [], dd or DrawdownMonitor(cap), ks or KillSwitch(LOCK))


results = []


def check(name, cond, info=""):
    results.append(cond)
    print(("PASS" if cond else "FAIL"), "|", name, info)


d = run(TradeRequest("EURUSD", "BUY", 1.10659, 1.10509, 0.0), eur)
check("EURUSD stop 15 pip lolos, lot 0.01", d.approved and d.lot == 0.01 and abs(d.risk_usd - 1.57) < 0.01, f"lot={d.lot} risiko={d.risk_usd:.2f}")

d = run(TradeRequest("USDJPY", "BUY", 159.919, 159.719, 0.0), jpy)
check("USDJPY stop 20 pip lolos", d.approved and d.lot == 0.01, f"lot={d.lot} risiko={d.risk_usd:.2f}")

d = run(TradeRequest("XAUUSD", "BUY", 3892.68, 3887.68, 0.04), xau)
check("XAUUSD stop $5 ditolak (lot min kegedean)", not d.approved, d.reasons)

d = run(TradeRequest("EURUSD", "BUY", 1.10659, 1.10509, 0.0), eur, cfg=exp)
check("Profil eksperimen -8% ditolak di modal 95", not d.approved, d.reasons)

d = run(TradeRequest("EURUSD", "BUY", 1.10659, 1.10809, 0.0), eur)
check("Stop di sisi salah ditolak", not d.approved, d.reasons)

d = run(TradeRequest("EURUSD", "BUY", 1.10659, 1.10509, 0.0), eur, valid=False)
check("Data tidak valid ditolak", not d.approved, d.reasons)

two = [{"symbol": "XAUUSD", "risk_usd": 1.0, "margin_usd": 2.0}, {"symbol": "USDJPY", "risk_usd": 1.0, "margin_usd": 1.0}]
d = run(TradeRequest("EURUSD", "BUY", 1.10659, 1.10509, 0.0), eur, open_pos=two)
check("Posisi terbuka penuh ditolak", not d.approved, d.reasons)

heavy = [{"symbol": "USDJPY", "risk_usd": 2.5, "margin_usd": 1.0}]
d = run(TradeRequest("EURUSD", "BUY", 1.10659, 1.10509, 0.0), eur, open_pos=heavy)
check("Total risiko melebihi batas ditolak", not d.approved, d.reasons)

d = run(TradeRequest("EURUSD", "BUY", 1.10659, 1.10509, 0.0003), eur)
check("Spread kelebaran ditolak", not d.approved, d.reasons)

dd = DrawdownMonitor(cap)
dd.update(89.0)
d = run(TradeRequest("EURUSD", "BUY", 1.10659, 1.10509, 0.0), eur, dd=dd)
check("Rugi sesi lewat batas ditolak (tanpa kill-switch)", not d.approved and not KillSwitch(LOCK).is_active(), d.reasons)

dd = DrawdownMonitor(cap)
dd.update(80.0)
ks = KillSwitch(LOCK)
d = run(TradeRequest("EURUSD", "BUY", 1.10659, 1.10509, 0.0), eur, dd=dd, ks=ks)
check("Drawdown total memicu kill-switch", not d.approved and ks.is_active(), d.reasons)

dd.update(95.0)
d = run(TradeRequest("EURUSD", "BUY", 1.10659, 1.10509, 0.0), eur, dd=dd, ks=ks)
check("Kill-switch tetap aktif walau equity pulih", not d.approved and ks.is_active(), d.reasons)

if os.path.exists(LOCK):
    os.remove(LOCK)
print(f"\n{sum(results)}/{len(results)} lolos")
