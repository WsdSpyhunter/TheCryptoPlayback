"""One-off: turn the Version 2 brand artwork (flat navy backgrounds) into transparent web PNGs.

Source files live in ~/Downloads/crypto-playback-newsletter zip/assets (not committed).
Outputs go to assets/v2/.  Run: python scripts/prep_v2_assets.py
"""
import os
import numpy as np
from PIL import Image

SRC = os.path.expanduser("~/Downloads/crypto-playback-newsletter zip/assets")
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "v2")
os.makedirs(OUT, exist_ok=True)


def key_out(img, bg, full=130.0):
    """Navy -> transparent. alpha grows with distance from bg; colour is un-premixed."""
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    bgc = np.array(bg, dtype=np.float32)
    d = np.sqrt(((a - bgc) ** 2).sum(axis=2))
    alpha = np.clip(d / full, 0, 1)
    alpha[d < 6] = 0
    safe = np.maximum(alpha, 1e-3)[..., None]
    fg = bgc + (a - bgc) / safe
    fg = np.clip(fg, 0, 255)
    out = np.dstack([fg, alpha * 255]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def trim(img, pad=0):
    bb = img.getchannel("A").point(lambda v: 255 if v > 10 else 0).getbbox()
    l, t, r, b = bb
    return img.crop((max(l - pad, 0), max(t - pad, 0), min(r + pad, img.width), min(b + pad, img.height)))


def fit_h(img, h):
    return img.resize((round(img.width * h / img.height), h), Image.LANCZOS)


def save(img, name):
    p = os.path.join(OUT, name)
    if name.endswith(".webp"):
        img.save(p, "WEBP", quality=90, method=6)
    else:
        img.save(p, optimize=True)
    print(name, img.size, os.path.getsize(p) // 1024, "KB")


# mascot (3000px, flat navy background)
m = Image.open(os.path.join(SRC, "Mascot navy background.png"))
bg = m.convert("RGB").getpixel((0, 0))
mk = trim(key_out(m, bg), pad=6)
save(fit_h(mk, 1500), "crypto-playback-mascot-bitcoin-uncle-sam-large.webp")
save(fit_h(mk, 760), "crypto-playback-mascot-bitcoin-uncle-sam.webp")
# head-and-shoulders crop for the round badge
w, h = mk.size
bust = mk.crop((int(w * 0.10), int(h * 0.20), int(w * 0.92), int(h * 0.80)))
save(fit_h(bust, 420), "crypto-playback-mascot-bust.webp")

# full wordmark ("The Crypto" ivory + "PlayBack" gold), already RGBA
wm = trim(Image.open(os.path.join(SRC, "TCP Title transparent.png")).convert("RGBA"), pad=4)
save(wm.resize((1600, round(wm.height * 1600 / wm.width)), Image.LANCZOS), "the-crypto-playback-logo.webp")
save(wm.resize((800, round(wm.height * 800 / wm.width)), Image.LANCZOS), "the-crypto-playback-logo-small.webp")

# --- favicon + social share card -------------------------------------------
from PIL import ImageDraw, ImageFont

NAVY = (11, 31, 58)
BRASS = (212, 176, 99)


def round_badge(size):
    """Mascot head-and-shoulders inside a brass ring on navy."""
    s = size * 4
    base = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    d.ellipse((0, 0, s - 1, s - 1), fill=NAVY + (255,))
    ring = max(2, s // 28)
    d.ellipse((ring // 2, ring // 2, s - 1 - ring // 2, s - 1 - ring // 2), outline=BRASS + (255,), width=ring)
    face = fit_h(bust, int(s * 0.74))
    base.alpha_composite(face, ((s - face.width) // 2, int(s * 0.17)))
    # clip to the circle
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, s - 1, s - 1), fill=255)
    base.putalpha(Image.composite(base.getchannel("A"), Image.new("L", (s, s), 0), mask))
    return base.resize((size, size), Image.LANCZOS)


save(round_badge(512), "the-crypto-playback-badge.webp")
round_badge(180).save(os.path.join(OUT, "apple-touch-icon.png"), optimize=True)
round_badge(64).save(os.path.join(OUT, "favicon.png"), optimize=True)


def font(path_or_none, size):
    p = os.path.expanduser("~/.cache/tcp-fonts/barlow-medium.ttf")
    if not os.path.exists(p):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        os.system(f'curl -sL "https://github.com/google/fonts/raw/main/ofl/barlowcondensed/BarlowCondensed-Medium.ttf" -o "{p}"')
    return ImageFont.truetype(p, size)


def share_card():
    W, H = 1200, 630
    card = Image.new("RGBA", (W, H), NAVY + (255,))
    d = ImageDraw.Draw(card)
    for x in range(0, W, 48):          # faint grid like the newsletter header
        d.line((x, 0, x, H), fill=(20, 44, 78, 255), width=1)
    for y in range(0, H, 48):
        d.line((0, y, W, y), fill=(20, 44, 78, 255), width=1)
    d.rectangle((0, H - 10, W, H), fill=(184, 147, 74, 255))   # brass rule
    m = fit_h(mk, 540)
    card.alpha_composite(m, (50, 36))
    wm_img = Image.open(os.path.join(OUT, "the-crypto-playback-logo.webp")).convert("RGBA")
    ww = 640
    wm2 = wm_img.resize((ww, round(wm_img.height * ww / wm_img.width)), Image.LANCZOS)
    card.alpha_composite(wm2, (470, 210))
    f = font(None, 38)
    d.text((470, 210 + wm2.height + 34), "DAILY BITCOIN & CRYPTO MARKET RESEARCH", font=f, fill=(201, 210, 224, 255))
    f2 = font(None, 30)
    d.text((470, 210 + wm2.height + 92), "16 LIVE INDICATORS  ·  FREE NEWSLETTER", font=f2, fill=BRASS + (255,))
    card.convert("RGB").save(os.path.join(OUT, "the-crypto-playback-share-card.png"), optimize=True)
    print("the-crypto-playback-share-card.png", (W, H))


share_card()
