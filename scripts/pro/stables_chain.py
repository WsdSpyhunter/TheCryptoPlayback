"""Basic Stablecoin Velocity & Flows, Open Edition: read straight from the blockchains.

No aggregator. Supply is read from each token's own contract (`totalSupply()`)
on free public nodes, Tron through TronGrid, Solana through the public RPC, and
Tether's own transparency feed is used as an issuer cross-check and for its
reserve figures.

What it measures
  Supply & net issuance   total supply of the tracked USD stablecoins and its change over
                          1 / 7 / 30 days. Because supply only changes when the issuer
                          mints or burns, the change IS net issuance (mint minus burn).
  Coins                   per-coin supply, share and change.
  Chain deployment        where supply sits and where new supply landed (7 / 30 days).
  Flow velocity           how fast net issuance is moving: average daily net issuance over
                          the last 7 days versus the 7 days before ("accelerating" /
                          "decelerating" / "reversing"). A flow-acceleration measure, not
                          payments velocity.
  Flow signal             z-score of the latest 7-day change versus the history we hold.
  Tether reserve cushion  Tether's published assets, liabilities and excess reserves.

History: daily supply at 00:00 UTC per coin and chain, kept in
data/pro/stable_chain_history.json. EVM history is back-filled with historical
`eth_call`s on free archive-capable nodes; Tron USDT history is replayed from
Tether's Issue / Redeem / DestroyedBlackFunds events; Solana has no free
historical-supply query, so Solana history accumulates from the first run.

Coverage is the top USD coins on eight chains (about 95% of USDT + USDC supply
plus the next largest coins). Not covered: smaller chains, euro and other
non-USD stablecoins, and exchange balances or transfer volume (no free source).
"""
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from .net import get_json, post_json, FetchError
from .stats import mean, stdev, clip

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HIST_FILE = os.path.join(ROOT, "data", "pro", "stable_chain_history.json")
DAY = 86400
BACKFILL_DAYS = 60
SELECTOR_TOTAL_SUPPLY = "0x18160ddd"

# archive-capable keyless nodes, tried in order (verified 2026-10-08)
EVM = {
    "Ethereum": {"bt": 12.0, "rpcs": ["https://rpc.mevblocker.io", "https://eth.drpc.org",
                                        "https://eth-mainnet.public.blastapi.io", "https://eth-pokt.nodies.app"]},
    "BSC": {"bt": 0.75, "rpcs": ["https://bsc-mainnet.public.blastapi.io"]},
    "Base": {"bt": 2.0, "rpcs": ["https://mainnet.base.org", "https://base.drpc.org", "https://base-mainnet.public.blastapi.io"]},
    "Arbitrum": {"bt": 0.25, "rpcs": ["https://arbitrum-one.public.blastapi.io"]},
    "Polygon": {"bt": 2.1, "rpcs": ["https://polygon.drpc.org"]},
    "Optimism": {"bt": 2.0, "rpcs": ["https://mainnet.optimism.io", "https://optimism.drpc.org"]},
    "Avalanche": {"bt": 2.0, "rpcs": ["https://api.avax.network/ext/bc/C/rpc"]},
}
# NOTE: BSC block time is ~0.75s in 2026 (post-Fermi); the estimator self-corrects, so this is only the first guess.

COINS = {
    "USDT": {"name": "Tether", "mech": "fiat-backed", "c": {
        "Ethereum": ("0xdAC17F958D2ee523a2206206994597C13D831ec7", 6),
        "Tron": ("TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t", 6)}},
    "USDC": {"name": "USD Coin", "mech": "fiat-backed", "c": {
        "Ethereum": ("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", 6),
        "Base": ("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", 6),
        "Arbitrum": ("0xaf88d065e77c8cC2239327C5EDb3A432268e5831", 6),
        "Polygon": ("0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", 6),
        "Optimism": ("0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85", 6),
        "Avalanche": ("0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E", 6),
        "Solana": ("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", 6)}},
    "USDS": {"name": "Sky USDS", "mech": "crypto-backed", "c": {"Ethereum": ("0xdC035D45d973E3EC169d2276DDab16f1e407384F", 18)}},
    "DAI": {"name": "Dai", "mech": "crypto-backed", "c": {"Ethereum": ("0x6B175474E89094C44Da98b954EedeAC495271d0F", 18)}},
    "USDe": {"name": "Ethena USDe", "mech": "crypto-backed", "c": {"Ethereum": ("0x4c9EDD5852cd905f086C759E8383e09bff1E68B3", 18)}},
    "USD1": {"name": "World Liberty USD1", "mech": "fiat-backed", "c": {
        "Ethereum": ("0x8d0D000Ee44948FC98c9B98A4FA4921476f08B0d", 18), "BSC": ("0x8d0D000Ee44948FC98c9B98A4FA4921476f08B0d", 18)}},
    "PYUSD": {"name": "PayPal USD", "mech": "fiat-backed", "c": {"Ethereum": ("0x6c3ea9036406852006290770BEdFcAbA0e23A0e8", 6)}},
    "RLUSD": {"name": "Ripple USD", "mech": "fiat-backed", "c": {"Ethereum": ("0x8292Bb45bf1Ee4d140127049757C2E0fF06317eD", 18)}},
    "FDUSD": {"name": "First Digital USD", "mech": "fiat-backed", "c": {
        "Ethereum": ("0xc5f0f7b66764F6ec8C8Dff7BA683102295E16409", 18), "BSC": ("0xc5f0f7b66764F6ec8C8Dff7BA683102295E16409", 18)}},
}

# USDT is tracked only where Tether itself issues AND the supply is not a bridged copy of Ethereum/Tron supply
# (Ethereum + Tron = about 97% of Tether's liabilities). Bridged or Binance-Peg copies on BSC, Polygon, Arbitrum
# and Optimism, and Binance-Peg USDC on BSC, would double count and are excluded. Tether also mints "authorised
# but unissued" tokens to its own treasury wallets, which are not in circulation, so for USDT:
#     circulating = totalSupply - balance of the Tether treasury wallet.
# (The sum then matches Tether's published liabilities; see the "tether" block in the output.)
TREASURY = {("USDT", "Ethereum"): "0x5754284f345afc66a98fbB0a0Afe71e0F007B949",
            ("USDT", "Tron"): "TKHuVq1oKVruCGLvqVexFs6dawKv6fQgFs"}

TRONGRID = "https://api.trongrid.io"
SOLANA_RPC = "https://api.mainnet-beta.solana.com"
TETHER_JSON = "https://app.tether.to/transparency.json"


def _rpc(chain, method, params):
    last = None
    for url in EVM[chain]["rpcs"]:
        try:
            r = post_json(url, {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, retries=2, timeout=25)
            if "result" in r and r["result"] is not None:
                return r["result"]
            last = r.get("error", r)
        except FetchError as exc:
            last = exc
    raise FetchError(f"{chain} {method} failed: {str(last)[:120]}")


def _supply_evm(chain, addr, dec, block="latest"):
    res = _rpc(chain, "eth_call", [{"to": addr, "data": SELECTOR_TOTAL_SUPPLY}, block])
    return int(res, 16) / 10 ** dec


def _block_ts(chain, number):
    b = _rpc(chain, "eth_getBlockByNumber", [hex(number), False])
    return int(b["timestamp"], 16)


def _latest(chain):
    return int(_rpc(chain, "eth_blockNumber", []), 16)


def block_at(chain, ts, latest=None, latest_ts=None):
    """Block number whose timestamp is just at or before `ts` (secant search; 3-4 lookups)."""
    latest = latest or _latest(chain)
    latest_ts = latest_ts or _block_ts(chain, latest)
    est = max(1, int(latest - (latest_ts - ts) / EVM[chain]["bt"]))
    for _ in range(5):
        t = _block_ts(chain, est)
        if abs(t - ts) <= EVM[chain]["bt"] * 2:
            return est
        # re-estimate with the locally observed block time
        ref = est + (1000 if est + 1000 <= latest else -1000)
        t2 = _block_ts(chain, ref)
        rate = abs((t2 - t) / (ref - est)) or EVM[chain]["bt"]
        est = max(1, int(est - (t - ts) / rate))
    return est


_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _tron_hex(addr):
    """Tron base58 address -> 20-byte hex (no 0x41 prefix)."""
    n = 0
    for ch in addr:
        n = n * 58 + _B58.index(ch)
    return f"{n:050x}"[2:-8]


def _balance_evm(chain, token, holder, block="latest"):
    data = "0x70a08231" + holder.lower().replace("0x", "").rjust(64, "0")
    return int(_rpc(chain, "eth_call", [{"to": token, "data": data}, block]), 16)


def _tron_balance(token, holder):
    r = post_json(f"{TRONGRID}/wallet/triggerconstantcontract",
                  {"owner_address": "T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb", "contract_address": token,
                   "function_selector": "balanceOf(address)", "parameter": _tron_hex(holder).rjust(64, "0"), "visible": True})
    return int(r["constant_result"][0], 16) / 1e6


def _tron_supply():
    r = post_json(f"{TRONGRID}/wallet/triggerconstantcontract",
                  {"owner_address": "T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb", "contract_address": COINS["USDT"]["c"]["Tron"][0],
                   "function_selector": "totalSupply()", "visible": True})
    return int(r["constant_result"][0], 16) / 1e6 - _tron_balance(COINS["USDT"]["c"]["Tron"][0], TREASURY[("USDT", "Tron")])


def _tron_treasury_flows(since_ts):
    """[(timestamp_s, signed_amount)]: USDT that LEFT (+) or ENTERED (-) circulation through the Tether
    Tron treasury since `since_ts`. Mints from / burns to the zero address are ignored (they are
    treasury-internal); transfers to/from anyone else change circulating supply."""
    treasury = TREASURY[("USDT", "Tron")]
    zero = "T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb"
    out, fingerprint = [], None
    for _ in range(120):
        params = {"only_confirmed": "true", "limit": 200, "contract_address": COINS["USDT"]["c"]["Tron"][0],
                  "min_timestamp": int(since_ts * 1000), "order_by": "block_timestamp,desc"}
        if fingerprint:
            params["fingerprint"] = fingerprint
        d = get_json(f"{TRONGRID}/v1/accounts/{treasury}/transactions/trc20", params=params, timeout=40)
        for e in d.get("data", []):
            amt = int(e["value"]) / 1e6
            if e["from"] == treasury and e["to"] != zero:
                out.append((e["block_timestamp"] / 1000.0, +amt))
            elif e["to"] == treasury and e["from"] != zero:
                out.append((e["block_timestamp"] / 1000.0, -amt))
        fingerprint = (d.get("meta") or {}).get("fingerprint")
        if not fingerprint:
            break
        time.sleep(0.2)
    return out


def _solana_supply(mint):
    r = post_json(SOLANA_RPC, {"jsonrpc": "2.0", "id": 1, "method": "getTokenSupply", "params": [mint]}, retries=3, timeout=25)
    v = r["result"]["value"]
    return int(v["amount"]) / 10 ** v["decimals"]


def _day_start(ts):
    return int(ts) // DAY * DAY


def _day_str(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")


def load_history():
    try:
        return json.load(open(HIST_FILE))
    except (OSError, ValueError):
        return {"series": {}, "meta": {}}


def save_history(h):
    os.makedirs(os.path.dirname(HIST_FILE), exist_ok=True)
    json.dump(h, open(HIST_FILE + ".tmp", "w"), separators=(",", ":"))
    os.replace(HIST_FILE + ".tmp", HIST_FILE)


def snapshot_now():
    """{(coin, chain): supply} for every tracked pair; failures are skipped and reported."""
    jobs = [(coin, chain, addr, dec) for coin, spec in COINS.items() for chain, (addr, dec) in spec["c"].items()]
    out, errs = {}, {}

    def one(j):
        coin, chain, addr, dec = j
        try:
            if chain == "Tron":
                return j, _tron_supply()
            if chain == "Solana":
                return j, _solana_supply(addr)
            v = _supply_evm(chain, addr, dec)
            if (coin, chain) in TREASURY:
                v -= _balance_evm(chain, addr, TREASURY[(coin, chain)]) / 10 ** dec
            return j, v
        except Exception as exc:       # noqa: BLE001
            return j, exc

    with ThreadPoolExecutor(max_workers=4) as ex:
        for j, v in ex.map(one, jobs):
            if isinstance(v, Exception):
                errs[f"{j[0]}|{j[1]}"] = str(v)[:100]
            else:
                out[(j[0], j[1])] = v
    return out, errs


def backfill_evm(hist, days=BACKFILL_DAYS):
    """Fill missing midnight-UTC supplies for EVM chains using historical eth_calls."""
    today0 = _day_start(time.time())
    want = [today0 - i * DAY for i in range(days, 0, -1)]            # oldest first, excludes today
    series = hist.setdefault("series", {})

    def chain_job(chain):
        pairs = [(c, a, d) for c, s in COINS.items() for ch, (a, d) in s["c"].items() if ch == chain]
        missing_days = [t for t in want if any(series.get(f"{c}|{chain}", {}).get(_day_str(t)) is None for c, _, _ in pairs)]
        if not missing_days:
            return chain, {}
        latest = _latest(chain)
        lts = _block_ts(chain, latest)
        found = {}
        for t in missing_days:
            try:
                blk = block_at(chain, t, latest, lts)
                for coin, addr, dec in pairs:
                    key = f"{coin}|{chain}"
                    if series.get(key, {}).get(_day_str(t)) is None:
                        v = _supply_evm(chain, addr, dec, hex(blk))
                        if (coin, chain) in TREASURY:
                            v -= _balance_evm(chain, addr, TREASURY[(coin, chain)], hex(blk)) / 10 ** dec
                        found.setdefault(key, {})[_day_str(t)] = v
            except Exception:       # noqa: BLE001 - node may not hold state this far back
                continue
        return chain, found

    with ThreadPoolExecutor(max_workers=4) as ex:
        for chain, found in ex.map(chain_job, EVM):
            for key, d in found.items():
                series.setdefault(key, {}).update(d)


def backfill_tron(hist, current_supply, days=BACKFILL_DAYS):
    """Rebuild Tron USDT circulating supply at past midnights from today's value and the treasury's
    transfers to/from the market (circulating then = circulating now - net outflow since then)."""
    today0 = _day_start(time.time())
    key = "USDT|Tron"
    s = hist.setdefault("series", {}).setdefault(key, {})
    need = [today0 - i * DAY for i in range(days, -1, -1) if s.get(_day_str(today0 - i * DAY)) is None or i == 0]
    if len(need) <= 1 and s.get(_day_str(today0 - DAY)) is not None:
        return 0
    flows = _tron_treasury_flows(today0 - (days + 1) * DAY)
    for t in need:
        net_out_since = sum(a for ts, a in flows if ts >= t)
        s[_day_str(t)] = current_supply - net_out_since
    return len(flows)


def record_today(hist, now_snap):
    """Store the latest observation under today's date (overwritten through the day)."""
    series = hist.setdefault("series", {})
    today = _day_str(time.time())
    for (coin, chain), v in now_snap.items():
        series.setdefault(f"{coin}|{chain}", {})[today] = v


def _trim(hist, keep=400):
    for k, s in hist.get("series", {}).items():
        for d in sorted(s)[:-keep]:
            s.pop(d)


def _series_total(series, keys, days):
    """Sum over `keys` for each day; only days where every key has a value."""
    out = []
    for d in days:
        vals = [series.get(k, {}).get(d) for k in keys]
        out.append(None if any(v is None for v in vals) else sum(vals))
    return out


def _chg(a, b):
    return None if a is None or not b else (a / b - 1.0) * 100.0


def compute(backfill=True):
    hist = load_history()
    now_snap, errs = snapshot_now()
    if not now_snap:
        raise RuntimeError("no stablecoin supply could be read from any node")
    # carry forward last known value for pairs that failed this run (flagged)
    series = hist.setdefault("series", {})
    today = _day_str(time.time())
    stale = []
    for coin, spec in COINS.items():
        for chain in spec["c"]:
            if (coin, chain) not in now_snap:
                last_days = sorted(series.get(f"{coin}|{chain}", {}))
                if last_days:
                    now_snap[(coin, chain)] = series[f"{coin}|{chain}"][last_days[-1]]
                    stale.append(f"{coin}|{chain}")
    if backfill:
        try:
            backfill_evm(hist)
        except Exception as exc:       # noqa: BLE001
            errs["backfill_evm"] = str(exc)[:100]
        try:
            if ("USDT", "Tron") in now_snap:
                n = backfill_tron(hist, now_snap[("USDT", "Tron")])
                errs.pop("tron_replay", None)
        except Exception as exc:       # noqa: BLE001
            errs["tron_replay"] = str(exc)[:100]
    record_today(hist, now_snap)
    _trim(hist)
    hist["meta"] = {"updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "stale_pairs": stale, "errors": errs}
    save_history(hist)
    series = hist["series"]

    # ---- aggregation
    all_keys = [f"{c}|{ch}" for c, s in COINS.items() for ch in s["c"]]
    days = sorted({d for k in all_keys for d in series.get(k, {})})[-(BACKFILL_DAYS + 1):]
    # history set = pairs with (nearly) complete history over the window; Solana builds up over time
    recent = days[-45:]
    full = [k for k in all_keys if all(series.get(k, {}).get(d) is not None for d in recent)]
    # ignore days before every history-set pair has data, so totals are like-for-like
    days = [d for d in days if all(series.get(k, {}).get(d) is not None for k in full)]
    total_now = sum(now_snap.values())
    tot_hist = _series_total(series, full, days)
    cov_now = sum(now_snap[(k.split("|")[0], k.split("|")[1])] for k in full if (k.split("|")[0], k.split("|")[1]) in now_snap)

    def at(back):
        return tot_hist[-1 - back] if len(tot_hist) > back else None
    last = tot_hist[-1]
    net = {n: (None if last is None or at(n) is None else last - at(n)) for n in (1, 7, 30)}
    chg = {n: (None if last is None else _chg(last, at(n))) for n in (1, 7, 30)}

    # per-coin
    coins = []
    for coin, spec in COINS.items():
        keys = [f"{coin}|{ch}" for ch in spec["c"]]
        fk = [k for k in keys if k in full]
        now_c = sum(now_snap.get((coin, ch), 0) for ch in spec["c"])
        ser = _series_total(series, fk, days)
        row = {"symbol": coin, "name": spec["name"], "mechanism": spec["mech"], "supply_usd": now_c, "share_pct": now_c / total_now * 100.0}
        for n in (1, 7, 30):
            row[f"change_{n}d_pct"] = _chg(ser[-1], ser[-1 - n]) if len(ser) > n and ser[-1] is not None and ser[-1 - n] else None
            row[f"net_{n}d_usd"] = (ser[-1] - ser[-1 - n]) if len(ser) > n and ser[-1] is not None and ser[-1 - n] is not None else None
        coins.append(row)
    coins.sort(key=lambda r: -r["supply_usd"])

    # per-chain
    chains = {}
    for coin, spec in COINS.items():
        for ch in spec["c"]:
            chains.setdefault(ch, []).append(f"{coin}|{ch}")
    chain_rows = []
    for ch, keys in chains.items():
        now_ch = sum(now_snap.get((k.split("|")[0], ch), 0) for k in keys)
        fk = [k for k in keys if k in full]
        ser = _series_total(series, fk, days) if fk else []
        r = {"chain": ch, "supply_usd": now_ch, "share_pct": now_ch / total_now * 100.0, "history_building": len(fk) < len(keys)}
        for n in (7, 30):
            r[f"net_{n}d_usd"] = (ser[-1] - ser[-1 - n]) if len(ser) > n and ser[-1] is not None and ser[-1 - n] is not None and len(fk) == len(keys) else None
        chain_rows.append(r)
    chain_rows.sort(key=lambda r: -r["supply_usd"])
    movers = sorted([r for r in chain_rows if r.get("net_7d_usd") is not None], key=lambda r: -abs(r["net_7d_usd"]))[:5]

    # flow velocity + signal from the daily total series
    daily_net = [None if tot_hist[i] is None or tot_hist[i - 1] is None else tot_hist[i] - tot_hist[i - 1] for i in range(1, len(tot_hist))]
    w7 = [x for x in daily_net[-7:] if x is not None]
    p7 = [x for x in daily_net[-14:-7] if x is not None]
    cur_rate = sum(w7) / len(w7) if len(w7) >= 5 else None
    prev_rate = sum(p7) / len(p7) if len(p7) >= 5 else None
    if cur_rate is None or prev_rate is None:
        vlabel = "Building history"
    elif cur_rate < 0 <= prev_rate or (cur_rate > 0 > prev_rate):
        vlabel = "Reversing"
    elif abs(cur_rate - prev_rate) < 0.15 * max(abs(prev_rate), 1e6):
        vlabel = "Steady"
    else:
        vlabel = "Accelerating" if abs(cur_rate) > abs(prev_rate) else "Decelerating"
    wk = [(_chg(tot_hist[i], tot_hist[i - 7]) if i >= 7 and tot_hist[i] is not None and tot_hist[i - 7] else None) for i in range(len(tot_hist))]
    past = [x for x in wk[:-1] if x is not None]
    z = None
    if wk[-1] is not None and len(past) >= 20 and stdev(past):
        z = clip((wk[-1] - mean(past)) / stdev(past), -4, 4)
    flabel = "Building history" if z is None else ("Expanding strongly" if z >= 1.5 else "Expanding" if z >= 0.5 else
                                                  "Contracting sharply" if z <= -1.5 else "Contracting" if z <= -0.5 else "Flat")

    # Tether's own figures
    tether = None
    try:
        td = get_json(TETHER_JSON, timeout=30)["data"]["usdt"]
        tot_tokens = sum(float(v) for k, v in td.items() if k.startswith("totaltokens_"))
        tether = {"liabilities_usd": float(td["total_liabilities"]), "assets_usd": float(td["total_assets"]),
                  "excess_reserves_usd": float(td["shareholder_eq"]),
                  "coverage_ratio": float(td["total_assets"]) / float(td["total_liabilities"]),
                  "tokens_all_chains_usd": tot_tokens,
                  "our_tracked_usdt_usd": sum(v for (c, ch), v in now_snap.items() if c == "USDT")}
    except Exception as exc:       # noqa: BLE001
        errs["tether_feed"] = str(exc)[:100]

    tail = slice(-(BACKFILL_DAYS), None)
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "status": "ok",
        "totals": {"supply_usd": total_now, "history_set_supply_usd": cov_now,
                   "change_1d_pct": chg[1], "change_7d_pct": chg[7], "change_30d_pct": chg[30],
                   "net_issuance_1d_usd": net[1], "net_issuance_7d_usd": net[7], "net_issuance_30d_usd": net[30]},
        "coins": coins, "chains": chain_rows[:10], "chain_movers": movers,
        "flow": {"z": None if z is None else round(z, 2), "label": flabel, "change_7d_pct": wk[-1]},
        "velocity": {"label": vlabel, "net_per_day_7d_usd": cur_rate, "net_per_day_prev_7d_usd": prev_rate},
        "tether": tether,
        "coverage": {"pairs_tracked": len(all_keys), "pairs_with_full_history": len(full), "stale_pairs": stale, "errors": errs,
                     "days_of_history": len(days)},
        "history": {"d": days[tail], "supply_usd": [None if v is None else round(v) for v in tot_hist[tail]],
                    "net_usd": [None if v is None else round(v) for v in ([None] + daily_net)[tail]]},
    }


if __name__ == "__main__":
    t0 = time.time()
    o = compute()
    print(f"{time.time() - t0:.0f}s")
    print(json.dumps({k: v for k, v in o.items() if k not in ("history", "coins", "chains")}, indent=1, default=str)[:3000])
    for c in o["coins"]:
        print(c["symbol"], round(c["supply_usd"] / 1e9, 2), "B", f"{c['share_pct']:.1f}%", "7d", c["change_7d_pct"] and round(c["change_7d_pct"], 2))
    for c in o["chains"]:
        print(c["chain"], round(c["supply_usd"] / 1e9, 2), "B", "7d net", c["net_7d_usd"] and round(c["net_7d_usd"] / 1e6), "M", "(building)" if c["history_building"] else "")
