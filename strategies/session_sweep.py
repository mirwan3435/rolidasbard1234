"""Plugin session_sweep. Hasilnya hipotesis sampai sampel tervalidasi."""
from strategies.common import SCHEMA, detect_session_sweep

id = "session_sweep"
kind = "detector"
source = "sample"
note = "Sweep range awal jendela. Hipotesis."
param_schema = SCHEMA


def detect(candles, ctx):
    return detect_session_sweep(candles, ctx)
