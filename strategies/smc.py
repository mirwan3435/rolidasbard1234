"""Plugin smc. Hasilnya hipotesis sampai sampel tervalidasi."""
from strategies.common import SCHEMA, detect_smc

id = "smc"
kind = "detector"
source = "sample"
note = "SMC: BOS terhadap swing. Hipotesis sampai PROFILER punya 100 trade."
param_schema = SCHEMA


def detect(candles, ctx):
    return detect_smc(candles, ctx)
