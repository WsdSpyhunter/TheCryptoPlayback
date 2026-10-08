"""Refresh all four institutional indicators and write data/pro/*.json.

Each indicator runs independently: if one source is down the others still
update, and the failed indicator keeps its last good file, marked stale.
Run:  python -m pro.refresh_pro [pressure basis regulatory miners unwind stables]
Exit code is 0 as long as at least one indicator refreshed.
"""
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone

from . import positioning, basis, regulatory, miners, unwind_chain, quality, stables_chain

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "data", "pro")
JOBS = {"pressure": positioning.compute, "basis": basis.compute, "regulatory": regulatory.compute, "miners": miners.compute, "unwind": unwind_chain.compute, "stables": stables_chain.compute}
# Offline (kept for later): DefiLlama-based Revenue / TVL Quality score. Move it back into JOBS and set
# SHOW_QUALITY = True in scripts/pro_page.py to publish it again (see docs/DATA-LICENSE-REVIEW.md first).
OFFLINE_JOBS = {"quality": quality.compute}


def _write(name, payload):
    os.makedirs(OUT, exist_ok=True)
    tmp = os.path.join(OUT, f".{name}.json.tmp")
    with open(tmp, "w") as f:
        json.dump(payload, f, separators=(",", ":"))
    os.replace(tmp, os.path.join(OUT, f"{name}.json"))


def main(names=None):
    names = names or list(JOBS)
    ok = []
    meta_path = os.path.join(OUT, "meta.json")
    try:
        meta = json.load(open(meta_path))
    except (OSError, ValueError):
        meta = {}
    for n in names:
        t0 = time.time()
        try:
            payload = JOBS[n]()
            _write(n, payload)
            ok.append(n)
            meta[n] = {"status": "ok", "updated_at": payload["updated_at"], "seconds": round(time.time() - t0, 1)}
            print(f"[{n}] ok in {time.time() - t0:.1f}s")
        except Exception as exc:           # noqa: BLE001 - isolate each indicator
            traceback.print_exc()
            meta[n] = {**meta.get(n, {}), "status": "stale", "error": f"{type(exc).__name__}: {str(exc)[:200]}",
                       "last_attempt": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            # mark the previous good file stale so the page can say so
            p = os.path.join(OUT, f"{n}.json")
            try:
                prev = json.load(open(p))
                prev["status"] = "stale"
                _write(n, prev)
            except (OSError, ValueError):
                pass
            print(f"[{n}] FAILED: {exc}")
    _write("meta", meta)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or None))
