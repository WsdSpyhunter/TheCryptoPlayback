"""Per-issue images for the Version 3 email: the header with that issue's date drawn in (the designer's
date font and position), and the sentiment gauge as a PNG (email apps strip inline SVG)."""
import math
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(ROOT, "assets", "fonts", "BarlowCondensed-Medium.ttf")
BASE_HEADER = os.path.join(ROOT, "assets", "email-v3-header.png")


def make_issue_header(dt, out_path):
    """The dateless header + '<WEEKDAY>, <MONTH> <D>, <YEAR>' at the designer's spot (x=424, baseline y=363 on the 2048px art)."""
    im = Image.open(BASE_HEADER).convert("RGB")
    d = ImageDraw.Draw(im)
    text = f"{dt.strftime('%A, %B')} {dt.day}, {dt.year}".upper()
    font = ImageFont.truetype(FONT, 44)
    x, spacing = 424.0, 6.2
    for ch in text:
        d.text((x, 363), ch, font=font, fill=(176, 193, 221), anchor="ls")
        x += d.textlength(ch, font=font) + spacing
    im.save(out_path, optimize=True)
    return out_path


def render_gauge_png(value, out_path):
    """Five-colour semicircle with a needle at `value` (0-100), same geometry as the website's gauge. 400x244."""
    S = 4                                       # draw big, then shrink for smooth edges
    W, H = 200 * S, 122 * S
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy, r, wd = 100 * S, 100 * S, 80 * S, 12 * S
    colors = ["#8E2B25", "#C98079", "#C9C2B0", "#6FA98A", "#1E7A4C"]
    bbox = (cx - r - wd // 2, cy - r - wd // 2, cx + r + wd // 2, cy + r + wd // 2)
    for i, c in enumerate(colors):
        d.arc(bbox, 180 + 36 * i, 180 + 36 * (i + 1), fill=c, width=wd)
    ang = math.radians(180 + max(0, min(100, value)) / 100 * 180)
    nx, ny = cx + 60 * S * math.cos(ang), cy + 60 * S * math.sin(ang)
    navy = "#0B1F3A"
    d.line([(cx, cy), (nx, ny)], fill=navy, width=3 * S)
    d.ellipse((cx - 6 * S, cy - 6 * S, cx + 6 * S, cy + 6 * S), fill=navy)
    f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 10 * S) if os.path.exists("/System/Library/Fonts/Supplemental/Arial.ttf") else ImageFont.load_default()
    for label, x in (("0", 20 * S), ("100", 180 * S)):
        d.text((x, 118 * S), label, font=f, fill="#5B6472", anchor="ms")
    im = im.resize((200 * 2, 122 * 2), Image.LANCZOS)
    im.save(out_path, optimize=True)
    return out_path


if __name__ == "__main__":
    from datetime import datetime
    make_issue_header(datetime(2026, 10, 5), "/tmp/hdr-issue.png")
    render_gauge_png(70, "/tmp/gauge.png")
    print("ok")
