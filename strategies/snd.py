"""Plugin snd. Hasilnya hipotesis sampai sampel tervalidasi."""
from strategies.common import SCHEMA, detect_snd

id = "snd"
kind = "detector"
source = "sample"
note = "Supply/demand sentuhan zona. Hipotesis."
param_schema = SCHEMA


def detect(candles, ctx):
    return detect_snd(candles, ctx)
