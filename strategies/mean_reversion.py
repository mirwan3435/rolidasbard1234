"""Plugin mean_reversion. Hasilnya hipotesis sampai sampel tervalidasi."""
from strategies.common import SCHEMA, detect_mean_reversion

id = "mean_reversion"
kind = "detector"
source = "sample"
note = "Mean reversion hanya saat range sempit. Hipotesis."
param_schema = SCHEMA


def detect(candles, ctx):
    return detect_mean_reversion(candles, ctx)
