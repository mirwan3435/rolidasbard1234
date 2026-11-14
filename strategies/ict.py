"""Plugin ict. Hasilnya hipotesis sampai sampel tervalidasi."""
from strategies.common import SCHEMA, detect_ict

id = "ict"
kind = "detector"
source = "sample"
note = "ICT: sweep lalu close kembali. Hipotesis."
param_schema = SCHEMA


def detect(candles, ctx):
    return detect_ict(candles, ctx)
