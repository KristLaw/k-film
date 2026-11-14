"""The darkroom: turns linear camera RGB into a film-looking print."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from .stocks import FilmStock

RAW_EXT = {".cr2", ".crw", ".dng", ".nef", ".arw", ".raf", ".orf", ".rw2"}

# 450D sensor: 4272 x 2848, 14-bit CR2 (decoded by LibRaw through rawpy).
CAMERA_450D = {"model": "Canon EOS 450D", "width": 4272, "height": 2848, "bits": 14}


# ---------------------------------------------------------------- loading
def srgb_to_linear(v: np.ndarray) -> np.ndarray:
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def load_linear(path: str | Path, half_size: bool = False) -> np.ndarray:
    """Return a float32 HxWx3 scene-linear image (mid grey ~0.18)."""
    path = Path(path)
    if path.suffix.lower() in RAW_EXT:
        import rawpy

        with rawpy.imread(str(path)) as raw:
            rgb = raw.postprocess(
                gamma=(1, 1), no_auto_bright=True, output_bps=16,
                use_camera_wb=True, half_size=half_size,
                output_color=rawpy.ColorSpace.sRGB,
            )
        # Linear 16-bit output: a correctly metered 18% grey lands near 0.18.
        return rgb.astype(np.float32) / 65535.0
    # JPEG/TIFF/PNG: useful for testing or for scanning old digital files.
    im = Image.open(path).convert("RGB")
    if half_size:
        im = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
    arr = np.asarray(im, dtype=np.float32) / 255.0
    return srgb_to_linear(arr).astype(np.float32)


# ---------------------------------------------------------------- helpers
def _box_blur(a: np.ndarray, r: int) -> np.ndarray:
    """Separable box blur on a 2-D array (edge padded)."""
    if r < 1:
        return a
    k = 2 * r + 1
    for axis in (0, 1):
        pad = [(0, 0), (0, 0)]
        pad[axis] = (r + 1, r)
        p = np.pad(a, pad, mode="edge")
        c = np.cumsum(p, axis=axis, dtype=np.float64)
        if axis == 0:
            a = (c[k:] - c[:-k]) / k
        else:
            a = (c[:, k:] - c[:, :-k]) / k
    return a.astype(np.float32)


def gaussian_blur(a: np.ndarray, sigma: float) -> np.ndarray:
    """Approximate gaussian with three box blurs."""
    r = max(1, int(round(sigma * 0.85)))
    for _ in range(3):
        a = _box_blur(a, r)
    return a


def _resize(a: np.ndarray, w: int, h: int) -> np.ndarray:
    return np.asarray(Image.fromarray(a.astype(np.float32), mode="F").resize((w, h), Image.BICUBIC))


def luminance(img: np.ndarray) -> np.ndarray:
    return img[..., 0] * 0.2126 + img[..., 1] * 0.7152 + img[..., 2] * 0.0722


# ---------------------------------------------------------------- stages
def film_curve(lin: np.ndarray, contrast: float, latitude: float,
               shift: float = 0.0, grey: float = 0.46) -> np.ndarray:
    """Log-domain S-curve. Input scene-linear, output display (0..1).

    ``shift`` (stops) moves one channel's curve to create colour crossover.
    The curve is bent so a neutral 18% grey prints at ``grey``.
    """
    lo, hi = -6.5 * latitude, 4.0 * latitude       # stops around mid grey
    k = 1.15 * contrast / latitude

    def curve(st, c):
        s = lambda x: 1.0 / (1.0 + np.exp(-k * (x - c)))
        return (s(st) - s(lo)) / (s(hi) - s(lo))

    gamma = np.log(grey) / np.log(curve(0.0, 0.0))
    stops = np.clip(np.log2(np.maximum(lin, 1e-7) / 0.18), lo, hi)
    return (np.clip(curve(stops, shift), 0.0, 1.0) ** gamma).astype(np.float32)


def add_halation(lin: np.ndarray, strength: float) -> np.ndarray:
    if strength <= 0:
        return lin
    h, w = lin.shape[:2]
    sw, sh = max(8, w // 4), max(8, h // 4)
    lum = luminance(lin)
    mask = np.clip((lum - 0.55) / 0.45, 0, 1) ** 2
    small = _resize(mask, sw, sh)
    glow = gaussian_blur(small, sigma=max(2.0, sw / 220))
    glow = _resize(glow, w, h)[..., None]
    tint = np.array([1.0, 0.28, 0.06], dtype=np.float32)   # red-orange
    return lin + glow * tint * strength * 2.5


def add_grain(y: np.ndarray, amount: float, size: float, mono: bool,
              rng: np.random.Generator, scale: float = 1.0) -> np.ndarray:
    """Luminance-weighted grain. ``scale`` keeps grain size consistent when
    the print is smaller than the full 450D frame."""
    if amount <= 0:
        return y
    h, w = y.shape[:2]
    cell = max(1.0, size * 1.6 * scale)
    gw, gh = max(4, int(w / cell)), max(4, int(h / cell))
    lum = luminance(y) if y.ndim == 3 else y
    weight = 0.25 + 3.0 * lum * (1.0 - lum)          # strongest in midtones

    def field():
        n = rng.standard_normal((gh, gw)).astype(np.float32)
        return _resize(n, w, h)

    g = field() * amount * weight
    out = y + g[..., None]
    if not mono:  # a little colour grain from the three dye layers
        for c in range(3):
            out[..., c] += field() * amount * 0.25 * weight
    return out


def vignette(y: np.ndarray, amount: float = 0.12) -> np.ndarray:
    h, w = y.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2) / np.sqrt(2)
    return y * (1.0 - amount * r ** 2.2)[..., None]


# ---------------------------------------------------------------- pipeline
def develop(lin: np.ndarray, stock: FilmStock, ev: float = 0.0,
            seed: int = 0, grain_scale: float = 1.0,
            lut=None) -> np.ndarray:
    """Develop one frame. Returns float32 HxWx3 display image in 0..1."""
    rng = np.random.default_rng(seed)
    img = lin.astype(np.float32) * (2.0 ** ev)
    img = img * np.array(stock.gain, dtype=np.float32)
    img = add_halation(img, stock.halation)

    if stock.kind == "bw":
        mix = np.array(stock.bw_mix, dtype=np.float32)
        mono = (img * mix).sum(axis=-1)
        y = film_curve(mono, stock.contrast, stock.latitude)
        y = np.repeat(y[..., None], 3, axis=-1)
    else:
        grey = 0.42 if stock.kind == "slide" else 0.46
        y = np.stack([film_curve(img[..., c], stock.contrast, stock.latitude,
                                 stock.crossover[c], grey) for c in range(3)], axis=-1)
        if stock.saturation != 1.0:
            l = luminance(y)[..., None]
            y = l + (y - l) * stock.saturation

    if lut is not None:
        y = lut.apply(np.clip(y, 0, 1))

    lum = luminance(np.clip(y, 0, 1))[..., None]
    y = y + np.array(stock.shadow_tint, np.float32) * (1 - lum) \
          + np.array(stock.highlight_tint, np.float32) * lum
    y = stock.fade + (1.0 - stock.fade) * y
    y = vignette(y, 0.10)
    y = add_grain(y, stock.grain, stock.grain_size, stock.kind == "bw", rng, grain_scale)
    return np.clip(y, 0.0, 1.0)


def to_image(y: np.ndarray) -> Image.Image:
    return Image.fromarray((np.clip(y, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB")


SIZES = {"full": None, "large": 3000, "web": 2048, "screen": 1080}


def print_frame(path: str | Path, stock: FilmStock, out: str | Path,
                size: str = "web", ev: float = 0.0, seed: int = 0,
                lut=None, quality: int = 92) -> Path:
    long_edge = SIZES[size]
    half = long_edge is not None and long_edge <= 2136   # half of 4272
    lin = load_linear(path, half_size=half)
    h, w = lin.shape[:2]
    if long_edge and max(h, w) > long_edge:
        s = long_edge / max(h, w)
        nw, nh = int(w * s), int(h * s)
        lin = np.stack([_resize(lin[..., c], nw, nh) for c in range(3)], -1)
    grain_scale = max(lin.shape[:2]) / CAMERA_450D["width"]
    y = develop(lin, stock, ev=ev, seed=seed, grain_scale=grain_scale, lut=lut)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    to_image(y).save(out, quality=quality)
    return out
