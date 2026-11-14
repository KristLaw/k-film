"""The M-Film lab, in numpy.

A Python port of the film model and print steps of M-Film's darkroom
(ml-dev/filmos/fos_dev.c, GPL-2.0, https://github.com/HNGSeries/mfilm-canon-film-simulation),
so the 72 M-Film films develop 450D RAWs the way M-Film does:

    daylight balance -> lab scanner exposure -> film's colour balance (K)
    -> optical softness -> halation -> vignette -> film colour (LUT or model)
    -> grain

Numbers follow the C code; the halation spread, softness and grain are
implemented with K-Film's own blur and noise, so prints are close to
M-Film's, not bit-identical.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from . import lut as lutmod
from .mfilm_films import FILMS

LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)
HUES = ["red", "orange", "yellow", "green", "cyan", "blue", "magenta"]
_REF = np.array([[1, 0, 0], [1, .5, 0], [1, 1, 0], [0, 1, 0], [0, 1, 1], [0, 0, 1], [1, 0, 1]], np.float32)


def lut_dir() -> Path:
    """Where `kfilm getluts` puts the Film-Luts collection (~/.kfilm/luts)."""
    return Path(os.environ.get("KFILM_LUTS", Path.home() / ".kfilm" / "luts"))


def find_lut(key: str):
    f = FILMS[key]
    name = f.get("lut")
    if not name:
        return None
    p = lut_dir() / name
    return lutmod.load(str(p), f.get("lut_space")) if p.is_file() else None


# ---------------------------------------------------------------- the film model
def _hue_angle(i: int) -> float:
    ref = _REF[i]
    y = float(ref @ LUMA)
    return float(np.arctan2((ref[0] - y) / 1.5748, (ref[2] - y) / 1.8556))


def _wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


def curve(x, slope, pivot, black, white):
    """The characteristic curve: logistic in log2 exposure around mid grey."""
    xx = np.log2(np.maximum(x, 1e-6) / 0.18) - pivot
    k = 4 * slope / (white - black)
    return black + (white - black) / (1 + np.exp(-k * xx))


def _shift_hues(f: dict, rgb: np.ndarray) -> np.ndarray:
    y = rgb @ LUMA
    cb = (rgb[..., 2] - y) / 1.8556
    cr = (rgb[..., 0] - y) / 1.5748
    h = np.arctan2(cr, cb)
    c = np.sqrt(cb * cb + cr * cr)
    gate = np.minimum(c / 0.04, 1)
    dh = np.zeros_like(h)
    cm = np.ones_like(h)
    sigma = np.radians(35)
    for a, b, amount, chroma in f.get("hues", []):
        hs = _hue_angle(HUES.index(a))
        w = np.exp(-0.5 * (_wrap(h - hs) / sigma) ** 2) * gate
        if a != b:
            dh += w * amount * _wrap(_hue_angle(HUES.index(b)) - hs)
        cm *= 1 + w * (chroma - 1)
    h = h + dh
    c = c * cm
    cb, cr = c * np.cos(h), c * np.sin(h)
    r = y + 1.5748 * cr
    bl = y + 1.8556 * cb
    g = (y - LUMA[0] * r - LUMA[2] * bl) / LUMA[1]
    return np.stack([r, g, bl], -1).astype(np.float32)


def film_color(f: dict, lin: np.ndarray) -> np.ndarray:
    """Scene-linear sRGB (0.18 = mid grey) -> the print, display sRGB 0..1."""
    con, piv, blk, wht = (list(f[k]) for k in ("contrast", "pivot", "black", "white"))
    if f.get("mono"):
        v = curve(lin @ np.array(f["mono"], np.float32), con[0], piv[0], blk[0], wht[0])
        return np.repeat(v[..., None], 3, -1).astype(np.float32)
    y = (lin @ LUMA)[..., None]
    x = np.maximum(y + (lin - y) * f.get("sat", 1.0), 0)
    out = np.stack([curve(x[..., c], con[c], piv[c], blk[c], wht[c]) for c in range(3)], -1)
    if f.get("hues"):
        out = _shift_hues(f, out)
    return out.astype(np.float32)


def cct_rgb(t: float) -> np.ndarray:
    """Linear sRGB of a blackbody at t kelvin (as cct_rgb in fos_dev.c)."""
    if t <= 4000:
        x = -0.2661239e9 / t**3 - 0.2343589e6 / t**2 + 0.8776956e3 / t + 0.179910
    else:
        x = -3.0258469e9 / t**3 + 2.1070379e6 / t**2 + 0.2226347e3 / t + 0.240390
    if t <= 2222:
        y = -1.1063814 * x**3 - 1.34811020 * x**2 + 2.18555832 * x - 0.20219683
    elif t <= 4000:
        y = -0.9549476 * x**3 - 1.37418593 * x**2 + 2.09137015 * x - 0.16748867
    else:
        y = 3.0817580 * x**3 - 5.87338670 * x**2 + 3.75112997 * x - 0.37001483
    X, Y, Z = x / y, 1.0, (1 - x - y) / y
    return np.array([3.2406 * X - 1.5372 * Y - 0.4986 * Z,
                     -0.9689 * X + 1.8758 * Y + 0.0415 * Z,
                     0.0557 * X - 0.2040 * Y + 1.0570 * Z])


def balance(kelvin: int) -> np.ndarray:
    """Multipliers that show daylight as a film balanced for `kelvin` sees it."""
    if kelvin == 5500:
        return np.ones(3, np.float32)
    a, b = cct_rgb(5500), cct_rgb(kelvin)
    bal = a / b
    return (bal / (a[1] / b[1])).astype(np.float32)


def scanner_ev(lin: np.ndarray, slide: bool) -> float:
    """The lab scanner: a negative's log-average luminance to a fixed key;
    a slide prints what was exposed."""
    if slide:
        return 1.0
    l = np.clip(lin[::4, ::4], 0, 1) @ LUMA
    key = float(np.exp(np.mean(np.log(l + 1e-4))))
    return float(np.clip(np.log2(0.11 / key), -2, 3.5))


# ---------------------------------------------------------------- the print
def develop(lin: np.ndarray, f: dict, ev: float = 0.0, seed: int = 0,
            scale: float = 1.0, use_lut: bool = True) -> np.ndarray:
    """Develop one frame with an M-Film film. `lin` must be daylight balanced.
    `scale` = print width / full sensor width (softness and grain sizes are
    given in full-resolution pixels)."""
    from .process import gaussian_blur, add_grain_field

    rng = np.random.default_rng(seed)
    img = np.clip(lin.astype(np.float32), 0, 1)
    k = 2.0 ** (scanner_ev(img, bool(f.get("slide"))) + f.get("ev", 0.0) + ev)
    img = img * k * balance(int(f.get("balance", 5500)))

    soft = f.get("soft", 0.0) * scale
    if soft >= 0.35:
        img = np.stack([gaussian_blur(img[..., c], soft) for c in range(3)], -1)

    h, w = img.shape[:2]
    if f.get("halation", 0) > 0:
        excess = np.maximum(img @ LUMA - f.get("hal_thr", 0.75), 0)
        glow = gaussian_blur(excess, max(1.0, 0.006 * w))
        tint = np.array(f.get("hal_tint", (1.0, 0.28, 0.06)), np.float32)
        img = img + glow[..., None] * f["halation"] * tint

    ty = np.linspace(-1, 1, h, dtype=np.float32)[:, None]
    tx = np.linspace(-1, 1, w, dtype=np.float32)[None, :]
    img = img * (1 - 0.06 * (tx * tx + ty * ty))[..., None]

    table = find_lut(f["_key"]) if use_lut and "_key" in f else None
    out = table.apply(img) if table is not None else film_color(f, img)

    g = f.get("grain", 0.0)
    if g > 0:
        out = add_grain_field(out, g * 0.55, f.get("grain_size", 1.0) * scale,
                              bool(f.get("mono")), rng)
    return np.clip(out, 0, 1).astype(np.float32)


def film(key: str) -> dict:
    d = dict(FILMS[key])
    d["_key"] = key
    return d
