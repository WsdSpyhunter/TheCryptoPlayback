"""
fetch_sentiment.py — pulls the current Crypto Fear & Greed Index.
Free public API, no key needed.
"""
import requests

API_URL = "https://api.alternative.me/fng/?limit=1"


def get_fear_greed():
    """Returns {'value': int, 'classification': str} e.g. {'value': 62, 'classification': 'Greed'}"""
    resp = requests.get(API_URL, timeout=15)
    resp.raise_for_status()
    data = resp.json()["data"][0]
    return {
        "value": int(data["value"]),
        "classification": data["value_classification"],
    }


if __name__ == "__main__":
    print(get_fear_greed())
