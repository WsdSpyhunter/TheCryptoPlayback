"""playback_take.py - "The Playback Take": a short section that connects the issue's news to the site's own
indicator readings (Signal Confluence, the Lab's Playback Read).

The writer model is given a plain list of the real indicator readings ("facts") and may only use numbers that
appear in it. Code then checks the result: every number it uses must be in the facts, no wording that claims one
thing caused another, and no predictions or advice. If anything fails, the section is dropped (a goal, not a
guarantee) and the issue goes out without it.
"""
import json
import os
import re
from html import unescape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BANNED = re.compile(
    r"\b(because|caused|causes|causing|due to|driven by|drove|led to|leading to|thanks to|as a result|triggered|"
    r"fueled|fuelled|resulted|will|going to|expected to|likely to|should|buy|sell|bullish|bearish)\b", re.I)
NUM = re.compile(r"\$?-?\d[\d,]*(?:\.\d+)?")


def _clean(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", unescape(s or ""))).strip()


def build_facts(live):
    """Plain-text readings the writer may use. `live` is build_site._live_context(...). Returns '' if unusable."""
    if not live or not live.get("confluence_items"):
        return ""
    lines = [f"Signal Confluence: {live['positive_count']} of {live['total_count']} signals are positive."]
    for name, pos, display in live["confluence_items"]:
        lines.append(f"- {_clean(name)}: {_clean(display)} ({'positive' if pos else 'negative'})")
    try:
        read = json.load(open(os.path.join(ROOT, "data", "pro", "read.json")))
        c = read["counts"]
        lines.append(f"Playback Lab read: {c['Supportive']} supportive, {c['Neutral']} neutral, {c['Caution']} caution.")
        for i in read["indicators"]:
            lines.append(f"- {_clean(i['name'])}: {i['label']} ({_clean(i['detail'])})")
    except (OSError, ValueError, KeyError):
        pass
    return "\n".join(lines)


def _nums(text):
    out = set()
    for m in NUM.findall(text or ""):
        out.add(m.replace("$", "").replace(",", "").rstrip("."))
    return out


def validate(take, facts):
    """Returns a cleaned take dict or None. Never raises."""
    try:
        if not isinstance(take, dict) or not facts:
            return None
        pts = take.get("points")
        tension, watch = take.get("tension"), take.get("watch")
        if not isinstance(pts, list) or not 2 <= len(pts) <= 3 or not all(isinstance(x, str) and x.strip() for x in (tension, watch)):
            return None
        clean_pts = []
        for p in pts:
            if not (isinstance(p, dict) and isinstance(p.get("label"), str) and isinstance(p.get("text"), str) and p["label"].strip() and p["text"].strip()):
                return None
            clean_pts.append({"label": p["label"].strip()[:28], "text": p["text"].strip()})
        allowed = _nums(facts)
        texts = [p["text"] for p in clean_pts] + [tension.strip(), watch.strip()]
        for t in texts:
            if len(t) > 260:
                print("playback_take: a sentence is too long - dropping the section.")
                return None
            if BANNED.search(t):
                print(f"playback_take: banned wording ({BANNED.search(t).group(0)!r}) - dropping the section.")
                return None
            extra = _nums(t) - allowed
            if extra:
                print(f"playback_take: numbers not in the indicator readings {sorted(extra)} - dropping the section.")
                return None
        return {"points": clean_pts, "tension": tension.strip(), "watch": watch.strip()}
    except Exception as exc:    # noqa: BLE001
        print(f"playback_take: check failed ({exc}) - dropping the section.")
        return None
