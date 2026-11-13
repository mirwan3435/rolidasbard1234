import pandas as pd
import MetaTrader5 as mt5
from data.market_data import connect, fetch_rates
from data.data_validator import validate_candles
from data.volume_profile import compute_volume_profile

print("--- tes sintetis ---")
rows = [{"high": 101, "low": 100, "tick_volume": 1000}] * 100
rows += [{"high": 110, "low": 100, "tick_volume": 100}] * 20
syn = pd.DataFrame(rows)
p = compute_volume_profile(syn, bins=10)
print("POC:", round(p["poc"], 2), "(harus sekitar 100-102)")
print("total volume cocok:", abs(p["volumes"].sum() - syn["tick_volume"].sum()) < 1e-6)

print("\n--- data asli ---")
connect()
for s in ["XAUUSD", "EURUSD", "USDJPY"]:
    df = fetch_rates(s, "M15", 1000)
    if not validate_candles(df, "M15").valid:
        print(s, "-> data INVALID, dilewati")
        continue
    p = compute_volume_profile(df, bins=50)
    last = df["close"].iloc[-1]
    pos = "di dalam value area" if p["val"] <= last <= p["vah"] else ("di atas VAH" if last > p["vah"] else "di bawah VAL")
    print(f"\n{s}  harga {last}  ({pos})")
    print(f"  POC {p['poc']:.5f} | VAL {p['val']:.5f} | VAH {p['vah']:.5f}")
    print("  HVN:", [round(x, 3) for x in p["hvn"]])
    print("  LVN:", [round(x, 3) for x in p["lvn"]])
    print("  urutan VAL<=POC<=VAH:", p["val"] <= p["poc"] <= p["vah"])
    print("  total volume cocok:", abs(p["volumes"].sum() - df["tick_volume"].sum()) < 1e-6)

mt5.shutdown()
