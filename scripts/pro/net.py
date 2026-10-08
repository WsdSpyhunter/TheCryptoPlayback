"""HTTP helper: retries with exponential backoff, polite headers, JSON parsing.

All collectors go through get_json()/post_json() so rate-limit handling and
failure behaviour live in one place. Public market-data endpoints only; no
API keys anywhere in this package.
"""
import json
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (compatible; CryptoPlaybackBot/1.0; +https://cryptoplayback.com)"}
_session = requests.Session()
_session.headers.update(UA)


class FetchError(RuntimeError):
    pass


def _request(method, url, params=None, body=None, timeout=30, retries=4, sleep_between=0.0):
    last = None
    for attempt in range(retries):
        try:
            if method == "GET":
                r = _session.get(url, params=params, timeout=timeout)
            else:
                r = _session.post(url, params=params, data=json.dumps(body),
                                  headers={"Content-Type": "application/json"}, timeout=timeout)
            if r.status_code in (429, 502, 503, 504):
                raise FetchError(f"{r.status_code} from {url}")
            if r.status_code >= 400:
                # 4xx other than rate limit will not fix itself (e.g. geo-block): fail fast
                raise FetchError(f"HTTP {r.status_code} from {url}: {r.text[:120]}")
            if sleep_between:
                time.sleep(sleep_between)
            return r.json()
        except (requests.RequestException, ValueError, FetchError) as exc:
            last = exc
            if isinstance(exc, FetchError) and "HTTP 4" in str(exc) and "429" not in str(exc):
                break
            time.sleep(min(2 ** attempt, 20))
    raise FetchError(f"{url} failed after {retries} attempts: {last}")


def get_json(url, params=None, **kw):
    return _request("GET", url, params=params, **kw)


def post_json(url, body, **kw):
    return _request("POST", url, body=body, **kw)
