"""Biaya satu trade. Angka komisi datang dari profil, tidak dikarang di sini."""


def trade_cost(spread_price, slippage_price, point_value, lot, commission_per_lot):
    spread_cost = max(0.0, float(spread_price)) * float(point_value) * float(lot)
    slip_cost = max(0.0, float(slippage_price)) * float(point_value) * float(lot)
    commission = float(commission_per_lot) * float(lot)
    return {
        "spread": spread_cost,
        "slippage": slip_cost,
        "commission": commission,
        "total": spread_cost + slip_cost + commission,
    }
