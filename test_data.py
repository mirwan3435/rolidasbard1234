import MetaTrader5 as mt5
from data.market_data import connect, fetch_rates, server_offset_hours

connect()
print("Offset server vs UTC (jam):", server_offset_hours())

for s in ["XAUUSD", "EURUSD", "USDJPY"]:
    df = fetch_rates(s, "M15", 1000)
    print(f"\n{s}: {len(df)} candle")
    print(df.tail(3).to_string(index=False))

mt5.shutdown()
