"""Plugin crt. Hasilnya hipotesis sampai sampel tervalidasi."""
from strategies.common import SCHEMA, detect_crt

id = "crt"
kind = "detector"
source = "sample"
note = "CRT: sweep candle acuan lalu close di dalam. Hipotesis."
param_schema = SCHEMA


def detect(candles, ctx):
    return detect_crt(candles, ctx)
