"""Similarity functions (physically interpretable, documented in scientific_methodology.md)."""
import math

FEATURES = ["lithology", "process", "landform", "resource", "slope", "ruggedness", "thermal", "aridity", "ice",
            "abiotic_surface", "dust_sediment"]


def canon(tag, equiv):
    return sorted(equiv.get(tag, [tag]))[0]


def jaccard(a, b, equiv):
    A = {canon(t, equiv) for t in a if t}
    B = {canon(t, equiv) for t in b if t}
    if not A or not B:
        return None
    return len(A & B) / len(A | B)


def gaussian(x, y, sigma):
    if x is None or y is None:
        return None
    return math.exp(-0.5 * ((x - y) / sigma) ** 2)


def slope_sim(med_e, p90_e, med_r, p90_r, s_med, s_p90):
    a, b = gaussian(med_e, med_r, s_med), gaussian(p90_e, p90_r, s_p90)
    if a is None or b is None:
        return None
    return 0.5 * a + 0.5 * b


def log_ratio(x, y, scale=1.0):
    if x is None or y is None or x <= 0 or y <= 0:
        return None
    return math.exp(-abs(math.log(x / y)) / scale)


def aridity_sim(ai, threshold=0.05, decay=0.15):
    if ai is None:
        return None
    return 1.0 if ai <= threshold else math.exp(-(ai - threshold) / decay)


def aridity_combined(ai, precip_mm, t=0.05, d=0.15, pt=50.0, pd=200.0):
    a = aridity_sim(ai, t, d)
    if precip_mm is None:
        return a
    b = 1.0 if precip_mm <= pt else math.exp(-(precip_mm - pt) / pd)
    return b if a is None else 0.5 * a + 0.5 * b


def agreement(x, y):
    if x is None or y is None:
        return None
    return 1.0 - abs(x - y)
