import numpy as np


def compute_volume_profile(df, bins=50, value_area=0.70, hvn_factor=1.3, lvn_factor=0.7):
    """Volume profile dari tick volume candle. Murni hitungan, tanpa AI."""
    if df is None or len(df) == 0:
        raise ValueError("DataFrame kosong")

    lo = float(df["low"].min())
    hi = float(df["high"].max())
    if hi <= lo:
        raise ValueError("Range harga nol")

    edges = np.linspace(lo, hi, bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2
    vol = np.zeros(bins)

    # Bagi volume tiap candle rata ke keranjang yang disentuh (low..high)
    for h, l, v in zip(df["high"].values, df["low"].values, df["tick_volume"].values):
        i0 = max(min(int(np.searchsorted(edges, l, side="right")) - 1, bins - 1), 0)
        i1 = max(min(int(np.searchsorted(edges, h, side="right")) - 1, bins - 1), 0)
        vol[i0:i1 + 1] += v / (i1 - i0 + 1)

    total = vol.sum()
    poc = int(vol.argmax())

    # Value area: mulai dari POC, melebar ke sisi yang volumenya lebih besar
    lo_i = hi_i = poc
    acc = vol[poc]
    while acc < value_area * total:
        up = vol[hi_i + 1] if hi_i + 1 < bins else -1
        dn = vol[lo_i - 1] if lo_i - 1 >= 0 else -1
        if up < 0 and dn < 0:
            break
        if up >= dn:
            hi_i += 1
            acc += up
        else:
            lo_i -= 1
            acc += dn

    # HVN / LVN: puncak dan lembah lokal dari profil yang diperhalus
    smooth = np.convolve(vol, np.ones(3) / 3, mode="same")
    mean = smooth.mean()
    hvn, lvn = [], []
    for i in range(1, bins - 1):
        if smooth[i] >= smooth[i - 1] and smooth[i] >= smooth[i + 1] and smooth[i] >= hvn_factor * mean:
            hvn.append(float(centers[i]))
        if smooth[i] <= smooth[i - 1] and smooth[i] <= smooth[i + 1] and smooth[i] <= lvn_factor * mean:
            lvn.append(float(centers[i]))

    return {
        "poc": float(centers[poc]),
        "vah": float(edges[hi_i + 1]),
        "val": float(edges[lo_i]),
        "hvn": hvn,
        "lvn": lvn,
        "centers": centers,
        "volumes": vol,
        "bins": bins,
    }
