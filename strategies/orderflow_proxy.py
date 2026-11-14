"""Plugin orderflow_proxy. Hasilnya hipotesis sampai sampel tervalidasi."""
from strategies.common import SCHEMA, detect_orderflow_proxy

id = "orderflow_proxy"
kind = "detector"
source = "sample"
note = "Konfirmasi saja. Tidak menghasilkan entry."
param_schema = SCHEMA


def detect(candles, ctx):
    return detect_orderflow_proxy(candles, ctx)
