from datetime import datetime, timezone, timedelta
from data.cot_data import get_cot

print("--- data asli ---")
for s in ["EURUSD", "USDJPY", "XAUUSD"]:
    r = get_cot(s)
    print(f"\n{s}  {'VALID' if r['valid'] else 'INVALID'}  {r['reasons']}")
    if "report_date" in r:
        print(f"  posisi: {r['report_date']} | rilis (perkiraan): {r['release_date_est']} | umur: {r['age_days']} hari")
    for g, v in r["groups"].items():
        print(f"  {g}: long {v['long']} short {v['short']} net {v['net']} | net_pair {v['net_pair']} | perubahan {v['change_net_pair']}")
    if r["warnings"]:
        print("  warning:", r["warnings"])

print("\n--- tes sabotase (harusnya False) ---")
future = datetime.now(timezone.utc) + timedelta(days=30)
print("data basi:", get_cot("EURUSD", now=future)["valid"])
