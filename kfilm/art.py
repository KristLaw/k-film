"""Karafilm pixel art: film canisters and the camera shelf pages.

Everything is drawn on a small grid of "cells" and blown up with hard
edges, in the style of classic pixel art: a dark outline, flat colour
bands for light, mid and shadow, and a light grey backdrop.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from . import pixelfont as pf

BRAND = "KARAFILM"

# ---------------------------------------------------------------- palette
BG = (212, 212, 216)          # the grey backdrop of the reference pixel art
BG_DARK = (186, 186, 192)
OUTLINE = (20, 20, 22)
INK = (28, 26, 24)
WHITE = (246, 244, 238)
METAL = [(26, 26, 30), (46, 46, 52), (70, 70, 78), (104, 104, 114), (150, 150, 160)]
LEADER = [(96, 52, 30), (142, 82, 46), (178, 110, 66)]   # orange-brown film base
DOTS = [(120, 196, 180), (238, 196, 140), (232, 120, 96)]  # mint, sand, coral

# label colours by shelf: (label, numerals, small text)
LABELS = {
    "Recipes": ((44, 30, 74), (255, 196, 70), (238, 150, 220)),
    "K-Film": ((22, 40, 56), (92, 200, 186), (236, 120, 96)),
    "color": ((24, 32, 44), (96, 188, 196), (236, 120, 96)),
    "slide": ((18, 34, 78), (250, 250, 240), (120, 190, 255)),
    "bw": ((30, 30, 30), (240, 240, 236), (170, 170, 170)),
    "print": ((60, 22, 22), (255, 182, 90), (240, 230, 210)),
}


def label_colours(film) -> tuple:
    if film.shelf in ("Recipes", "K-Film"):
        return LABELS[film.shelf]
    if film.engine == "mfilm" and film.data.get("kind") in ("print", "cine"):
        return LABELS["print"]
    return LABELS.get(film.kind, LABELS["color"])


def _band(d, x0, y0, x1, y1, cols):
    """Vertical shading across a cylinder: cols from left (lit) to right."""
    n = len(cols)
    w = x1 - x0 + 1
    for i in range(w):
        t = i / max(1, w - 1)
        # light comes from the left: mid, highlight, mid, shadow, deep shadow
        k = [2, 3, 4, 3, 2, 2, 1, 1, 0][min(8, int(t * 9))]
        d.line([(x0 + i, y0), (x0 + i, y1)], fill=cols[min(k, n - 1)])


def canister(film, cells: int = 1, leader: bool = True) -> Image.Image:
    """A 35 mm canister, 64 x 92 cells, with the Karafilm label and the
    film leader coming out of its lips."""
    W, H = 96, 92
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    lab, num, small = label_colours(film)

    # film leader, behind the can: sprocketed strip leaving to the right
    if leader:
        _leader(d)
    _can(im, d, film, lab, num, small)
    if not leader:
        im = im.crop((0, 0, 56, H))
    if cells > 1:
        im = im.resize((im.width * cells, H * cells), Image.NEAREST)
    return im


def _leader(d):
    d.rectangle([40, 30, 93, 70], fill=OUTLINE)
    d.rectangle([41, 31, 92, 69], fill=LEADER[1])
    d.rectangle([41, 31, 92, 33], fill=LEADER[2])
    d.rectangle([41, 66, 92, 69], fill=LEADER[0])
    for x in range(48, 92, 7):
        for y in (35, 61):
            d.rectangle([x, y, x + 3, y + 3], fill=OUTLINE)
    # cut end: the leader's tongue is narrower, as on a real roll
    d.rectangle([80, 30, 93, 49], fill=(0, 0, 0, 0))
    d.rectangle([80, 49, 93, 49], fill=OUTLINE)
    d.rectangle([93, 49, 93, 70], fill=OUTLINE)
    d.rectangle([79, 30, 79, 49], fill=OUTLINE)


def _can(im, d, film, lab, num, small):
    # spool post on top
    d.rectangle([22, 2, 33, 9], fill=OUTLINE)
    _band(d, 23, 3, 32, 8, METAL)
    # top cap
    d.rectangle([4, 9, 51, 15], fill=OUTLINE)
    _band(d, 5, 10, 50, 14, METAL)
    # body
    d.rectangle([7, 15, 48, 82], fill=OUTLINE)
    _band(d, 8, 16, 47, 81, METAL)
    # bottom cap
    d.rectangle([4, 82, 51, 88], fill=OUTLINE)
    _band(d, 5, 83, 50, 87, METAL)
    d.rectangle([22, 88, 33, 90], fill=OUTLINE)

    # the label, wrapped round the body
    d.rectangle([9, 19, 46, 79], fill=lab)
    shade = tuple(max(0, c - 18) for c in lab)
    d.rectangle([38, 19, 46, 79], fill=shade)                # far side in shadow
    d.line([(9, 19), (46, 19)], fill=tuple(min(255, c + 30) for c in lab))
    # three dots
    for i, c in enumerate(DOTS):
        cx = 12 + i * 6
        d.rectangle([cx, 22, cx + 3, 25], fill=c)
        d.point([(cx, 22), (cx + 3, 22), (cx, 25), (cx + 3, 25)], fill=lab)
    # brand down the label, then the speed big
    pf.draw(im, (12, 29), "KARA", 1, small)
    pf.draw(im, (12, 37), "FILM", 1, small)
    iso = str(film.iso)
    scale = 2 if len(iso) <= 3 else 1
    pf.draw(im, (11, 50), iso, scale, num, spacing=1)
    pf.draw(im, (11, 50 + 7 * scale + 3), f"{film.frames}EXP", 1, small)
    # highlight glint on the metal
    d.line([(14, 16), (14, 18)], fill=METAL[4])
    d.line([(14, 80), (14, 81)], fill=METAL[4])


def pixelate(img: Image.Image, cells_w: int, cells_h: int, colours: int = 48) -> Image.Image:
    """A photo as pixel art: shrunk to the grid, fewer colours, no dither."""
    small = img.convert("RGB").resize((cells_w, cells_h), Image.BOX)
    return small.quantize(colours, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert("RGB")


def _frame(d, box, fill=OUTLINE):
    x0, y0, x1, y1 = box
    d.rectangle([x0 - 2, y0 - 2, x1 + 2, y1 + 2], fill=fill)


# ---------------------------------------------------------------- camera pages
PAGE_W, PAGE_H, CELL = 282, 188, 8      # 2256 x 1504: the 450D's own S size


def compact(s) -> list[str]:
    """CameraSettings in three short lines for the page."""
    if s.style == "Monochrome":
        b = f"SHARP {s.sharpness}  CONTRAST {s.contrast:+d}"
    else:
        b = f"SH{s.sharpness} CON{s.contrast:+d} SAT{s.saturation:+d} TONE{s.color_tone:+d}"
    c = f"WB {s.wb.upper()}" + (f" {s.shift}" if s.shift != "0" else "") + ("  HTP ON" if s.htp else "")
    return [f"STYLE {s.style.upper()}", b, c]


def page(film, cam, sample: Image.Image | None,
         n: int, total: int, iso_text: str) -> Image.Image:
    """One shelf page, 3:2, for the 450D's Playback screen."""
    im = Image.new("RGB", (PAGE_W, PAGE_H), BG)
    d = ImageDraw.Draw(im)
    # backdrop: a darker floor the canister stands on
    d.rectangle([0, 150, PAGE_W, PAGE_H], fill=BG_DARK)
    d.rectangle([0, 0, PAGE_W - 1, 13], fill=OUTLINE)
    pf.draw(im, (6, 4), f"{BRAND} SHELF", 1, (255, 196, 70))
    pf.draw(im, (PAGE_W - 6 - pf.width(f"{n:02d}/{total}", 1), 4), f"{n:02d}/{total}", 1, WHITE)
    shelf = film.shelf.upper()
    pf.draw(im, ((PAGE_W - pf.width(shelf, 1)) // 2, 4), shelf, 1, (150, 150, 160))

    # canister with a soft pixel shadow
    can = canister(film)
    d.rectangle([12, 142, 70, 147], fill=(160, 160, 168))
    im.paste(can, (8, 52), can)

    # sample print in a film frame, top right
    fx0, fy0, fw, fh = 116, 22, 156, 102
    d.rectangle([fx0 - 6, fy0 - 9, fx0 + fw + 5, fy0 + fh + 8], fill=OUTLINE)
    for x in range(fx0 - 3, fx0 + fw + 3, 7):
        d.rectangle([x, fy0 - 7, x + 3, fy0 - 5], fill=BG)
        d.rectangle([x, fy0 + fh + 4, x + 3, fy0 + fh + 6], fill=BG)
    if sample is not None:
        im.paste(pixelate(sample, fw, fh), (fx0, fy0))
    else:
        d.rectangle([fx0, fy0, fx0 + fw - 1, fy0 + fh - 1], fill=(60, 60, 66))
        pf.draw(im, (fx0 + 40, fy0 + 48), "NO SAMPLE", 1, (150, 150, 160))

    # name and settings, bottom right
    name = film.name.upper()
    scale = 2 if pf.width(name, 2) <= PAGE_W - 114 else 1
    pf.draw(im, (110, 134 + (0 if scale == 2 else 4)), name, scale, INK)
    accent = (110, 60, 170) if film.shelf == "Recipes" else (30, 110, 120)
    pf.draw(im, (110, 150), f"{film.id.upper()} · {iso_text}", 1, accent)
    for i, line in enumerate(compact(cam)):
        pf.draw(im, (110, 160 + 9 * i), line, 1, (64, 64, 70))
    # left: what the camera needs, under the canister
    pf.draw(im, (8, 160), "SHOOT RAW", 1, INK)
    pf.draw(im, (8, 169), "REVIEW OFF", 1, INK)
    return im.resize((PAGE_W * CELL, PAGE_H * CELL), Image.NEAREST)


def cover(films: list, total: int) -> Image.Image:
    im = Image.new("RGB", (PAGE_W, PAGE_H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 150, PAGE_W, PAGE_H], fill=BG_DARK)
    pf.draw(im, (18, 16), BRAND, 4, OUTLINE)
    pf.draw(im, (20, 50), "A FILM SHELF FOR THE CANON EOS 450D", 1, (70, 70, 76))
    pf.draw(im, (20, 60), f"{total} FILMS  ·  TURN THE DIAL TO BROWSE", 1, (70, 70, 76))
    # one of each shelf, standing in a row, the last one with its leader out
    by_id = {f.id: f for f in films}
    picks = [by_id[k] for k in ("reggieportra", "portra400", "velvia50", "trix400") if k in by_id]
    for i, f in enumerate(picks):
        can = canister(f, leader=(i == len(picks) - 1))
        d.rectangle([18 + i * 60, 158, 70 + i * 60, 162], fill=(160, 160, 168))
        im.paste(can, (12 + i * 60, 70), can)
    pf.draw(im, (20, 172), "ON THE COMPUTER:  KFILM LOAD <ID>", 1, INK)
    return im.resize((PAGE_W * CELL, PAGE_H * CELL), Image.NEAREST)


def _wrap(text: str, width: int) -> list[str]:
    words, out, cur = text.split(" "), [], ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) > width:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}" if cur else w
    if cur:
        out.append(cur)
    return out


def load_sample(path: Path) -> Image.Image | None:
    try:
        return Image.open(path).convert("RGB")
    except (OSError, ValueError):
        return None


_CHART_CACHE: dict = {}


def chart_sample(film, chart: Path) -> Image.Image:
    """A sample print developed from the built-in test chart (no M-Film folder)."""
    from .mfilm import develop as mdev
    from .process import develop, srgb_to_linear, to_image
    if chart not in _CHART_CACHE:
        src = Image.open(chart).convert("RGB")
        w, h = src.size
        _CHART_CACHE[chart] = srgb_to_linear(
            np.asarray(src.crop((0, 0, w // 3, h // 2)).resize((312, 208)), np.float32) / 255)
    lin = _CHART_CACHE[chart]
    y = (develop(lin, film.stock, seed=1, grain_scale=0.1) if film.engine == "kfilm"
         else mdev(lin, film.data, seed=1, scale=0.1))
    return to_image(y)
