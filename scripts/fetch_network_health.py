"""
fetch_network_health.py — Bitcoin network hash rate, difficulty-adjustment
trend, and mempool congestion from mempool.space's free public API (no key,
no auth).
"""
import requests

HASHRATE_URL = "https://mempool.space/api/v1/mining/hashrate/3d"
DIFFICULTY_URL = "https://mempool.space/api/v1/difficulty-adjustment"
FEES_URL = "https://mempool.space/api/v1/fees/recommended"
MEMPOOL_URL = "https://mempool.space/api/mempool"


def get_network_health():
    resp = requests.get(HASHRATE_URL, timeout=15)
    resp.raise_for_status()
    hashrate_eh = resp.json()["currentHashrate"] / 1e18  # H/s -> EH/s

    resp = requests.get(DIFFICULTY_URL, timeout=15)
    resp.raise_for_status()
    difficulty_change_pct = resp.json()["difficultyChange"]

    resp = requests.get(FEES_URL, timeout=15)
    resp.raise_for_status()
    fastest_fee_satvb = resp.json()["fastestFee"]

    resp = requests.get(MEMPOOL_URL, timeout=15)
    resp.raise_for_status()
    pending_tx_count = resp.json()["count"]

    return {
        "hashrate_eh": hashrate_eh,
        "difficulty_change_pct": difficulty_change_pct,
        "fastest_fee_satvb": fastest_fee_satvb,
        "pending_tx_count": pending_tx_count,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(get_network_health(), indent=2))
