"""Plugin wyckoff. Hasilnya hipotesis sampai sampel tervalidasi."""
from strategies.common import SCHEMA, detect_wyckoff

id = "wyckoff"
kind = "detector"
source = "sample"
note = "Spring/upthrust. Hipotesis."
param_schema = SCHEMA


def detect(candles, ctx):
    return detect_wyckoff(candles, ctx)
