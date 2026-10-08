"""Derivatives collectors (free public endpoints, no keys).

Venues: OKX, Gate.io, Hyperliquid, Bitget, Deribit (BTC/ETH), Kraken Futures.
Binance and Bybit are NOT used: both refuse US IP addresses (GitHub Actions
runs in the US), verified 2026-10-07.

Two kinds of function live here:
  * snapshot_*  - one call for the whole venue: current OI (USD), funding
                  normalised to a per-8-hours rate, mark price.
  * history_*   - hourly (or 8-hourly) series with real history, so the
                  indicators can be scored over 30 days from the first run.

Funding conventions: every funding rate is converted to the equivalent of a
single 8-hour period as a plain decimal (0.0001 = 0.01% per 8h).
"""
import time
from concurrent.futures import ThreadPoolExecutor

from .net import get_json, post_json, FetchError

ASSETS = ["BTC", "ETH", "SOL", "XRP", "DOGE", "BNB", "ADA", "AVAX", "LINK", "SUI"]

OKX = "https://www.okx.com/api/v5"
GATE = "https://api.gateio.ws/api/v4/futures/usdt"
HL = "https://api.hyperliquid.xyz/info"
BITGET = "https://api.bitget.com/api/v2/mix/market"
DERIBIT = "https://www.deribit.com/api/v2/public"
KRAKEN_F = "https://futures.kraken.com/derivatives/api/v3"


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


# ----------------------------- snapshots ----------------------------------

def snapshot_okx():
    """OI from the all-SWAP call (USDT- and coin-margined summed); funding per asset."""
    out = {a: {"oi_usd": 0.0, "funding_8h": None, "mark": None} for a in ASSETS}
    oi = get_json(f"{OKX}/public/open-interest", params={"instType": "SWAP"})["data"]
    for row in oi:
        inst = row["instId"]                     # e.g. BTC-USDT-SWAP, BTC-USD-SWAP
        base = inst.split("-")[0]
        if base in out and inst.endswith(("-USDT-SWAP", "-USD-SWAP")):
            out[base]["oi_usd"] += _f(row.get("oiUsd")) or 0.0

    def one(a):
        d = get_json(f"{OKX}/public/funding-rate", params={"instId": f"{a}-USDT-SWAP"})["data"][0]
        rate = _f(d.get("fundingRate"))
        t0, t1 = _f(d.get("fundingTime")), _f(d.get("nextFundingTime"))
        hours = (t1 - t0) / 3.6e6 if t0 and t1 and t1 > t0 else 8.0
        return a, (rate * 8.0 / hours if rate is not None else None)

    with ThreadPoolExecutor(max_workers=5) as ex:
        for a, f in ex.map(one, ASSETS):
            out[a]["funding_8h"] = f
    return out


def snapshot_gate():
    out = {}
    for c in get_json(f"{GATE}/contracts"):
        name = c.get("name", "")
        a = name.replace("_USDT", "")
        if a in ASSETS and name.endswith("_USDT"):
            mark, mult = _f(c.get("mark_price")), _f(c.get("quanto_multiplier"))
            size = _f(c.get("position_size"))
            interval = (_f(c.get("funding_interval")) or 28800) / 3600.0
            rate = _f(c.get("funding_rate"))
            out[a] = {
                "oi_usd": size * mult * mark if None not in (size, mult, mark) else None,
                "funding_8h": rate * 8.0 / interval if rate is not None else None,
                "mark": mark,
            }
    return out


def snapshot_hyperliquid():
    meta, ctxs = post_json(HL, {"type": "metaAndAssetCtxs"})
    out = {}
    for u, c in zip(meta["universe"], ctxs):
        a = u["name"]
        if a in ASSETS:
            mark = _f(c.get("markPx"))
            oi = _f(c.get("openInterest"))
            fr = _f(c.get("funding"))       # Hyperliquid funding is an HOURLY rate
            out[a] = {"oi_usd": oi * mark if None not in (oi, mark) else None,
                      "funding_8h": fr * 8.0 if fr is not None else None, "mark": mark}
    return out


def snapshot_bitget():
    out = {}
    for t in get_json(f"{BITGET}/tickers", params={"productType": "USDT-FUTURES"})["data"]:
        sym = t.get("symbol", "")
        a = sym.replace("USDT", "")
        if a in ASSETS and sym.endswith("USDT"):
            mark, hold = _f(t.get("lastPr")), _f(t.get("holdingAmount"))
            out[a] = {"oi_usd": hold * mark if None not in (hold, mark) else None,
                      "funding_8h": _f(t.get("fundingRate")), "mark": mark}   # 8h on Bitget USDT-M
    return out


def snapshot_deribit():
    out = {}
    for a in ("BTC", "ETH"):
        r = get_json(f"{DERIBIT}/ticker", params={"instrument_name": f"{a}-PERPETUAL"})["result"]
        out[a] = {"oi_usd": _f(r.get("open_interest")),          # Deribit perp OI is quoted in USD
                  "funding_8h": _f(r.get("funding_8h")), "mark": _f(r.get("mark_price"))}
    return out


def snapshot_kraken_futures():
    out = {}
    alias = {"XBT": "BTC"}
    for t in get_json(f"{KRAKEN_F}/tickers")["tickers"]:
        sym = t.get("symbol", "")
        if not (sym.startswith("PF_") and sym.endswith("USD")):
            continue
        a = sym[3:-3]
        a = alias.get(a, a)
        if a in ASSETS:
            mark, oi, fr = _f(t.get("markPrice")), _f(t.get("openInterest")), _f(t.get("fundingRate"))
            # Kraken's fundingRate is an absolute hourly amount per contract unit -> relative, then x8
            out[a] = {"oi_usd": oi * mark if None not in (oi, mark) else None,
                      "funding_8h": (fr / mark) * 8.0 if None not in (fr, mark) and mark else None,
                      "mark": mark}
    return out


VENUES = {
    "OKX": snapshot_okx,
    "Gate": snapshot_gate,
    "Hyperliquid": snapshot_hyperliquid,
    "Bitget": snapshot_bitget,
    "Deribit": snapshot_deribit,
    "Kraken": snapshot_kraken_futures,
}


def collect_snapshots():
    """{venue: {asset: {...}}}; a venue that fails is skipped (and reported)."""
    snaps, errors = {}, {}
    for name, fn in VENUES.items():
        try:
            snaps[name] = fn()
        except (FetchError, KeyError, IndexError, TypeError) as exc:
            errors[name] = str(exc)[:160]
    return snaps, errors


def aggregate_asset(snaps, asset):
    """OI-weighted funding across venues + dispersion. Returns dict or None."""
    rows = []
    for v, per in snaps.items():
        d = per.get(asset)
        if d and d.get("oi_usd") and d.get("funding_8h") is not None:
            rows.append((v, d["oi_usd"], d["funding_8h"], d.get("mark")))
    if not rows:
        return None
    tot = sum(r[1] for r in rows)
    fw = sum(r[1] * r[2] for r in rows) / tot
    mean_f = sum(r[2] for r in rows) / len(rows)
    var = sum((r[2] - mean_f) ** 2 for r in rows) / len(rows)
    return {
        "oi_usd": tot,
        "funding_8h": fw,
        "funding_dispersion": var ** 0.5,
        "venues": [{"venue": r[0], "oi_usd": r[1], "funding_8h": r[2]} for r in sorted(rows, key=lambda r: -r[1])],
    }


# ----------------------------- history ------------------------------------

def history_gate(asset, hours=720):
    """Hourly contract stats from Gate for `asset`: OI (USD), long/short ratios,
    funding, liquidations, mark. Pages of 500 rows, oldest first."""
    end = int(time.time())
    start = end - hours * 3600
    rows, cursor = [], start
    while cursor < end:
        page = get_json(f"{GATE}/contract_stats",
                        params={"contract": f"{asset}_USDT", "interval": "1h", "from": cursor, "limit": 500})
        if not page:
            break
        rows.extend(page)
        last = page[-1]["time"]
        if last <= cursor or len(page) < 500:
            break
        cursor = last + 3600
    seen, out = set(), []
    for r in rows:
        t = r["time"]
        if t in seen:
            continue
        seen.add(t)
        out.append({
            "t": t,
            "oi_usd": _f(r.get("open_interest_usd")),
            "lsr_account": _f(r.get("lsr_account")),
            "lsr_taker": _f(r.get("lsr_taker")),
            "top_lsr_account": _f(r.get("top_lsr_account")),
            "funding": _f(r.get("last_funding_rate")),       # per funding interval (Gate: 8h on majors)
            "long_liq_usd": _f(r.get("long_liq_usd_new")) or _f(r.get("long_liq_usd")) or 0.0,
            "short_liq_usd": _f(r.get("short_liq_usd_new")) or _f(r.get("short_liq_usd")) or 0.0,
            "mark": _f(r.get("mark_price")),
        })
    out.sort(key=lambda x: x["t"])
    return out


def history_okx_oi(ccy="BTC"):
    """OKX hourly aggregate OI (USD) + volume for a currency (about 30 days)."""
    rows = get_json(f"{OKX}/rubik/stat/contracts/open-interest-volume", params={"ccy": ccy, "period": "1H"})["data"]
    return sorted(({"t": int(r[0]) // 1000, "oi_usd": _f(r[1]), "vol_usd": _f(r[2])} for r in rows), key=lambda x: x["t"])


def history_okx_lsr(ccy="BTC"):
    rows = get_json(f"{OKX}/rubik/stat/contracts/long-short-account-ratio", params={"ccy": ccy, "period": "1H"})["data"]
    return sorted(({"t": int(r[0]) // 1000, "lsr": _f(r[1])} for r in rows), key=lambda x: x["t"])


def history_okx_funding(asset, pages=4):
    """8h-equivalent funding history from OKX (100 rows per page, newest first)."""
    out, after = [], None
    for _ in range(pages):
        params = {"instId": f"{asset}-USDT-SWAP", "limit": 100}
        if after:
            params["after"] = after
        rows = get_json(f"{OKX}/public/funding-rate-history", params=params)["data"]
        if not rows:
            break
        for r in rows:
            out.append({"t": int(r["fundingTime"]) // 1000, "funding_8h": _f(r.get("realizedRate") or r.get("fundingRate"))})
        after = rows[-1]["fundingTime"]
        if len(rows) < 100:
            break
    out.sort(key=lambda x: x["t"])
    return out


def history_hyperliquid_funding(asset, days=30):
    """Hourly funding history (converted to 8h equivalents), 500-row pages by startTime."""
    start = int((time.time() - days * 86400) * 1000)
    out = []
    for _ in range(8):
        rows = post_json(HL, {"type": "fundingHistory", "coin": asset, "startTime": start})
        if not rows:
            break
        for r in rows:
            out.append({"t": int(r["time"]) // 1000, "funding_8h": _f(r["fundingRate"]) * 8.0})
        nxt = int(rows[-1]["time"]) + 1
        if nxt <= start or len(rows) < 100:
            break
        start = nxt
    out.sort(key=lambda x: x["t"])
    return out
