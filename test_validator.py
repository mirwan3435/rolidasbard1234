import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime, timezone, timedelta
from data.market_data import connect, fetch_rates
from data.data_validator import validate_candles

connect()

print("--- data asli (harusnya VALID) ---")
for s in ["XAUUSD", "EURUSD", "USDJPY"]:
    r = validate_candles(fetch_rates(s, "M15", 1000), "M15")
    print(s, "VALID" if r.valid else "INVALID", r.reasons, r.warnings[:2])

print("\n--- tes sabotase (harusnya False semua) ---")
df = fetch_rates("EURUSD", "M15", 200)

x = df.copy()
x.loc[x.index[-5], "high"] = x.loc[x.index[-5], "low"] - 0.01
print("high<low  :", validate_candles(x).valid)

x = df.copy()
x.loc[x.index[-5], "close"] = float("nan")
print("nilai NaN :", validate_candles(x).valid)

print("duplikat  :", validate_candles(pd.concat([df, df.tail(1)], ignore_index=True)).valid)

x = df.drop(df.index[100:120]).reset_index(drop=True)
print("gap besar :", validate_candles(x).valid)

future = datetime.now(timezone.utc) + timedelta(hours=3)
print("data stale:", validate_candles(df, now=future).valid)

mt5.shutdown()
