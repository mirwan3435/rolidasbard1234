"""Plugin breakout. Hasilnya hipotesis sampai sampel tervalidasi."""
from strategies.common import SCHEMA, detect_breakout

id = "breakout"
kind = "detector"
source = "sample"
note = "Breakout close di luar range. Hipotesis."
param_schema = SCHEMA


def detect(candles, ctx):
    return detect_breakout(candles, ctx)
