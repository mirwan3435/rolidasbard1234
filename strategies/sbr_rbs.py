"""Plugin sbr_rbs. Hasilnya hipotesis sampai sampel tervalidasi."""
from strategies.common import SCHEMA, detect_sbr_rbs

id = "sbr_rbs"
kind = "detector"
source = "sample"
note = "SBR/RBS tes ulang level jebol. Hipotesis."
param_schema = SCHEMA


def detect(candles, ctx):
    return detect_sbr_rbs(candles, ctx)
