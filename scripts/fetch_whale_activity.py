"""
fetch_whale_activity.py — large BTC transactions from blockchain.info's free
public unconfirmed-transactions API (no key, no auth). Samples the most
recent 1000 mempool transactions and returns each one's total output value
in BTC (a standard, if approximate, proxy for "amount moved" - it can
slightly overcount real value moved since change outputs returning coins to
the sender are included too, same simplification most free whale-tracking
tools make).

Returns raw BTC amounts only - classifying which of those count as a
"whale" transaction depends on the current USD price, which this module
doesn't fetch (that's fetch_prices.py's job); build_site.py does that
conversion using the price it already has for the homepage.
"""
import requests

API_URL = "https://blockchain.info/unconfirmed-transactions"
SAMPLE_SIZE = 1000
MIN_BTC_FLOOR = 5.0  # drop obviously-not-whale-sized txs before returning, to keep the payload small


def get_large_transaction_amounts():
    resp = requests.get(API_URL, params={"format": "json", "limit": SAMPLE_SIZE}, timeout=20)
    resp.raise_for_status()
    txs = resp.json()["txs"]

    amounts_btc = []
    for tx in txs:
        total_btc = sum(o["value"] for o in tx["out"]) / 1e8
        if total_btc >= MIN_BTC_FLOOR:
            amounts_btc.append(total_btc)

    return {
        "amounts_btc": sorted(amounts_btc, reverse=True),
        "sample_size": len(txs),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(get_large_transaction_amounts(), indent=2))
