"""Builds the email-safe image assets for the Version 3 newsletter (run by hand when the artwork changes).

  assets/email-v3/icon-<key>-<tone>.png   line icons as PNGs (email apps strip inline SVG); tone = ink (on light) / gold (on dark)
  assets/email-v3/arrow-notable.png       the curved arrow beside the "A story you may have missed" badge
  assets/email-v3-header.png              the designer's header with the baked-in date painted out (the date is live text)
"""
import os
import subprocess
import tempfile

from PIL import Image

import v2_ui as ui

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "email-v3")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
TONES = {"ink": "#8A6A1F", "gold": "#D4B063"}
CELL = 96


def render_icons():
    keys = sorted(ui.ICON_PATHS)
    cols = 8
    rows = (len(keys) * len(TONES) + cols - 1) // cols
    cells, order = [], []
    for k in keys:
        for tone, color in TONES.items():
            order.append((k, tone))
            cells.append(f'<div style="width:{CELL}px;height:{CELL}px;display:flex;align-items:center;justify-content:center;">'
                         f'<svg width="{CELL - 16}" height="{CELL - 16}" viewBox="0 0 48 48" fill="none" stroke="{color}" stroke-width="2.4" '
                         f'stroke-linecap="round" stroke-linejoin="round">{ui.ICON_PATHS[k]}</svg></div>')
    html = (f'<html><body style="margin:0;background:transparent"><div style="display:grid;grid-template-columns:repeat({cols},{CELL}px);">'
            + "".join(cells) + "</div></body></html>")
    with tempfile.TemporaryDirectory() as td:
        hp, sp = os.path.join(td, "i.html"), os.path.join(td, "i.png")
        open(hp, "w").write(html)
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--default-background-color=00000000",
                        f"--window-size={cols * CELL},{rows * CELL}", f"--screenshot={sp}", f"file://{hp}"],
                       check=True, capture_output=True)
        sheet = Image.open(sp).convert("RGBA")
    os.makedirs(OUT, exist_ok=True)
    for i, (k, tone) in enumerate(order):
        x, y = (i % cols) * CELL, (i // cols) * CELL
        sheet.crop((x, y, x + CELL, y + CELL)).save(os.path.join(OUT, f"icon-{k}-{tone}.png"), optimize=True)
    return len(order)


def render_arrow():
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="160" height="144" viewBox="0 0 80 72" fill="none">'
           '<path d="M80 16 C48 12 22 22 24 52" stroke="#0B1F3A" stroke-width="3" stroke-linecap="round"/>'
           '<path d="M15 53 L24 69 L33 53 Z" fill="#0B1F3A"/></svg>')
    with tempfile.TemporaryDirectory() as td:
        hp, sp = os.path.join(td, "a.html"), os.path.join(td, "a.png")
        open(hp, "w").write(f'<html><body style="margin:0;background:transparent">{svg}</body></html>')
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--default-background-color=00000000",
                        "--window-size=160,144", f"--screenshot={sp}", f"file://{hp}"], check=True, capture_output=True)
        Image.open(sp).convert("RGBA").save(os.path.join(OUT, "arrow-notable.png"), optimize=True)


def make_dateless_header(src):
    """Paint the baked-in date (it sits on plain navy, clear of the candlesticks) out of the designer's header."""
    im = Image.open(src).convert("RGB")
    w, h = im.size
    box = (int(w * 0.19), int(h * 0.70), int(w * 0.47), int(h * 0.88))      # the date line
    sample = im.getpixel((int(w * 0.19), int(h * 0.93)))                     # plain navy just below
    patch = Image.new("RGB", (box[2] - box[0], box[3] - box[1]), sample)
    im.paste(patch, box[:2])
    im.save(os.path.join(ROOT, "assets", "email-v3-header.png"), optimize=True)


if __name__ == "__main__":
    print("icons:", render_icons())
    render_arrow()
    src = os.path.expanduser("~/Downloads/crypto-playback-newsletter zip/assets/TCP_Header_1_2.png")
    make_dateless_header(src)
    print("done")
