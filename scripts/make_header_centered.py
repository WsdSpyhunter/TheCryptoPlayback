"""Rebuilds the newsletter header art (assets/email-v3-header.png) with the mascot + title + tagline group slid
toward the centre while the candlestick chart stays exactly where the designer put it. Run by hand when the artwork
changes; the per-issue date is drawn on top by email_images.make_issue_header (it uses the same SHIFT).

The designer's PNG has the date and a thin white edge baked in, so this:
  1. trims the white edge,
  2. rebuilds the background under the mascot / title / tagline / date (candle lines are re-drawn across the gaps),
  3. pastes the mascot and the title + tagline back SHIFT pixels to the right.
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from email_images import HDR_SCALE, HDR_CX, HDR_CY, HDR_SHIFT

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.expanduser("~/Downloads/crypto-playback-newsletter zip/assets/TCP_Header_1_2.png")
OUT = os.path.join(ROOT, "assets", "email-v3-header.png")
if not os.path.exists(SRC):
    SRC = os.path.join(ROOT, "docs", "newsletter-v3-design", "assets", "TCP_Header_1_2.png")
SHIFT = HDR_SHIFT            # pixels (on the 2042px-wide art) the group moves right
TRIM = 3                     # white edge to cut off
LINE_MIN = 40                # luminance above which a pixel can be part of a candle line


def dilate(mask, r):
    out = mask.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r:
                out |= np.roll(np.roll(mask, dy, axis=0), dx, axis=1)
    return out


def box_blur(a, r):
    """Separable box blur of a 2-D or 3-D float array (edges handled by the caller's normalisation)."""
    k = 2 * r + 1
    out = a
    for axis in (0, 1):
        c = np.cumsum(np.pad(out, [(r + 1, r) if i == axis else (0, 0) for i in range(out.ndim)], mode="edge"), axis=axis)
        sl_hi = [slice(None)] * out.ndim; sl_lo = [slice(None)] * out.ndim
        sl_hi[axis] = slice(k, None); sl_lo[axis] = slice(0, -k)
        out = (c[tuple(sl_hi)] - c[tuple(sl_lo)]) / k
    return out


def fill_holes(img, hole):
    """Rebuild the background under `hole`: a smooth estimate of the plain background (from the pixels around it),
    plus the candle lines, redrawn straight across each gap (vertical lines from the pixels above/below, horizontal
    edges from the pixels left/right)."""
    h, w, _ = img.shape
    f = img.astype(float)
    lum = f.sum(axis=2) / 3.0
    plain = (~hole) & (lum < LINE_MIN)                      # real background pixels only (no candle lines)
    wgt = box_blur(plain.astype(float), 22)
    smooth = box_blur(f * plain[..., None], 22) / np.maximum(wgt, 1e-3)[..., None]
    flat = np.array([10.0, 30.0, 55.0])
    smooth = np.where((wgt > 0.05)[..., None], smooth, flat)

    line_v = np.zeros((h, w), bool); line_h = np.zeros((h, w), bool)
    val_v = np.zeros_like(f); val_h = np.zeros_like(f)
    for axis, flag, val in ((0, line_v, val_v), (1, line_h, val_h)):
        for i in (range(w) if axis == 0 else range(h)):
            line = hole[:, i] if axis == 0 else hole[i, :]
            n = len(line); j = 0
            while j < n:
                if not line[j]:
                    j += 1; continue
                k = j
                while k < n and line[k]:
                    k += 1
                a_, b_ = j - 1, k
                if a_ >= 0 and b_ < n:
                    ca = f[a_, i] if axis == 0 else f[i, a_]
                    cb = f[b_, i] if axis == 0 else f[i, b_]
                    la, lb = ca.sum() / 3.0, cb.sum() / 3.0
                    if la > LINE_MIN and lb > LINE_MIN and abs(la - lb) < 25 and la < 95 and lb < 95:   # a candle line runs through the gap
                        c = (ca + cb) / 2.0
                        if axis == 0:
                            flag[j:k, i] = True; val[j:k, i] = c
                        else:
                            flag[i, j:k] = True; val[i, j:k] = c
                j = k
    res = f.copy()
    res[hole] = smooth[hole]
    use_h = hole & line_h & ~line_v
    res[use_h] = val_h[use_h]
    res[hole & line_v] = val_v[hole & line_v]
    return res


def build():
    im = Image.open(SRC).convert("RGB")
    w0, h0 = im.size
    im = im.crop((TRIM, TRIM, w0 - TRIM, h0 - TRIM))
    a = np.asarray(im).astype(float)
    h, w, _ = a.shape
    lum = a.sum(axis=2) / 3.0
    ox = TRIM                                              # original -> cropped coordinates

    mascot_box = np.zeros((h, w), bool)
    mascot_box[60 - ox:430 - ox, 70 - ox:360 - ox] = True
    bright = lum > 95
    bright[:, :380 - ox] = False                           # text lives right of the mascot
    text_all = dilate(bright, 3)                           # title + tagline + date, with their soft edges
    date_rows = np.zeros((h, w), bool)
    date_rows[312 - ox:392 - ox, 405 - ox:1005 - ox] = True
    text_keep = text_all & ~date_rows                      # what moves: title + tagline (the date is redrawn live)
    hole = mascot_box | text_all | date_rows               # the whole old date band is rebuilt (the date is redrawn live)

    bg = fill_holes(np.asarray(im), hole)                  # background + candles without the group

    # soft alpha masks for the pieces we paste back
    def soft(mask, blur):
        m = Image.fromarray((mask * 255).astype(np.uint8))
        from PIL import ImageFilter
        return np.asarray(m.filter(ImageFilter.GaussianBlur(blur))).astype(float) / 255.0

    out = bg.copy()
    sc = HDR_SCALE
    coef = (1 / sc, 0, HDR_CX - (HDR_CX + SHIFT) / sc, 0, 1 / sc, HDR_CY - HDR_CY / sc)   # output -> input (scale about the anchor, then shift)
    src_img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    moved = np.asarray(src_img.transform((w, h), Image.AFFINE, coef, Image.BICUBIC)).astype(float)
    for mask, blur in ((mascot_box, 6), (text_keep, 0.8)):
        alpha_img = Image.fromarray((soft(mask, blur) * 255).astype(np.uint8))
        alpha = np.asarray(alpha_img.transform((w, h), Image.AFFINE, coef, Image.BICUBIC)).astype(float) / 255.0
        out = out * (1 - alpha[..., None]) + moved * alpha[..., None]
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(OUT, optimize=True)
    return OUT, (w, h)


if __name__ == "__main__":
    print(build())
