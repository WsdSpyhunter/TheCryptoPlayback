"""Small statistics toolkit shared by the institutional indicators (pure Python)."""
import math


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def stdev(xs):
    xs = [x for x in xs if x is not None]
    if len(xs) < 2:
        return None
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def clip(x, lo, hi):
    return max(lo, min(hi, x))


def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2)))


def percentile_rank(value, sample):
    """Share of `sample` at or below `value`, 0-100 (mid-rank for ties)."""
    sample = [s for s in sample if s is not None]
    if not sample or value is None:
        return None
    below = sum(1 for s in sample if s < value)
    equal = sum(1 for s in sample if s == value)
    return 100.0 * (below + 0.5 * equal) / len(sample)


def zscore_series(values, min_window=24, max_window=720, clip_at=3.0):
    """Trailing z-score of each point against the points BEFORE it (no look-ahead).
    Uses an expanding window until `max_window` points exist; None until `min_window`."""
    out = []
    for i, v in enumerate(values):
        if v is None:
            out.append(None)
            continue
        past = [x for x in values[max(0, i - max_window):i] if x is not None]
        if len(past) < min_window:
            out.append(None)
            continue
        sd = stdev(past)
        if not sd:
            out.append(0.0)
            continue
        out.append(clip((v - mean(past)) / sd, -clip_at, clip_at))
    return out


def rolling_mean(values, window):
    out = []
    for i in range(len(values)):
        chunk = [x for x in values[max(0, i - window + 1):i + 1] if x is not None]
        out.append(sum(chunk) / len(chunk) if chunk else None)
    return out


def pct_change(series, lag):
    out = []
    for i, v in enumerate(series):
        j = i - lag
        if j < 0 or v is None or series[j] in (None, 0):
            out.append(None)
        else:
            out.append((v / series[j] - 1.0) * 100.0)
    return out


def ffill(values):
    last, out = None, []
    for v in values:
        if v is not None:
            last = v
        out.append(last)
    return out
