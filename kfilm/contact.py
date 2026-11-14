"""Contact sheets: strips of developed film, drawn in K-Film's pixel style."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from . import pixelfont as pf



# K-Film colours: darkroom black, safelight amber, paper cream
INK = (17, 15, 13)
AMBER = (255, 176, 32)
AMBER_DARK = (122, 70, 0)
CREAM = (238, 232, 218)
MUTED = (150, 140, 124)
CELL = 4                                   # one "pixel" of the pixel style


def _snap(v: int) -> int:
    return v // CELL * CELL


def pixel_logo(img: Image.Image, xy, scale: int = 4) -> int:
    """The K-FILM label: a tiny pixel film canister, then the name."""
    x, y = xy
    d = ImageDraw.Draw(img)
    s = scale
    # canister: cap, body with a band, film leader sticking out
    d.rectangle([x + s, y, x + 4 * s - 1, y + s - 1], fill=MUTED)
    d.rectangle([x, y + s, x + 5 * s - 1, y + 7 * s - 1], fill=AMBER)
    d.rectangle([x, y + 3 * s, x + 5 * s - 1, y + 4 * s - 1], fill=INK)
    d.rectangle([x + s, y + 7 * s, x + 4 * s - 1, y + 8 * s - 1], fill=MUTED)
    d.rectangle([x + 5 * s, y + 5 * s, x + 8 * s - 1, y + 7 * s - 1], fill=AMBER_DARK)
    return pf.draw(img, (x + 10 * s, y + s // 2), "K-FILM", s, AMBER, shadow=AMBER_DARK)


def light_leak(img: Image.Image, seed: int, strength: float = 0.8) -> Image.Image:
    """Orange/red fog from one edge, as if the back was opened."""
    rng = np.random.default_rng(seed)
    a = np.asarray(img, dtype=np.float32) / 255.0
    h, w = a.shape[:2]
    x = np.linspace(0, 1, w, dtype=np.float32)[None, :]
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    side = rng.integers(0, 2)
    d = x if side == 0 else 1 - x
    wobble = 0.08 * np.sin(y * rng.uniform(3, 7) * np.pi + rng.uniform(0, 6))
    m = np.clip(1.0 - (d + wobble) / rng.uniform(0.35, 0.6), 0, 1) ** 1.6 * strength
    color = np.array([1.0, 0.45, 0.12], dtype=np.float32)
    a = 1 - (1 - a) * (1 - m[..., None] * color)      # screen blend
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def contact_sheet(prints: list[Path], stock, out: Path,
                  per_row: int = 6, thumb_w: int = 300) -> Path:
    """A sheet of film strips with the K-FILM label, in the pixel style."""
    thumb_w = _snap(thumb_w)
    thumb_h = _snap(int(thumb_w * 2 / 3))  # 3:2 like the 450D and 35 mm
    gap = 4 * CELL
    pad = 12 * CELL                          # room for sprockets + edge print
    rows = max(1, (len(prints) + per_row - 1) // per_row)
    strip_h = thumb_h + pad * 2
    W = per_row * (thumb_w + gap) + gap + 10 * CELL
    H = rows * (strip_h + 6 * CELL) + 32 * CELL
    sheet = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(sheet)
    edge = AMBER if stock.kind != "bw" else CREAM
    x_end = pixel_logo(sheet, (5 * CELL, 4 * CELL), scale=6)
    pf.draw(sheet, (x_end + 8 * CELL, 5 * CELL), f"{stock.name}", 3, CREAM)
    pf.draw(sheet, (x_end + 8 * CELL, 5 * CELL + 30),
            f"ISO {stock.iso}  ·  {len(prints)} FRAMES  ·  CANON EOS 450D", 2, MUTED)

    film_base = (34, 27, 20) if stock.kind != "bw" else (28, 28, 26)
    for r in range(rows):
        y0 = 26 * CELL + r * (strip_h + 6 * CELL)
        d.rectangle([5 * CELL, y0, W - 5 * CELL - 1, y0 + strip_h - 1], fill=film_base)
        for sx in range(8 * CELL, W - 8 * CELL, 6 * CELL):      # square sprocket holes
            for sy in (y0 + 2 * CELL, y0 + strip_h - 5 * CELL):
                d.rectangle([sx, sy, sx + 3 * CELL - 1, sy + 3 * CELL - 1], fill=INK)
        for c in range(per_row):
            i = r * per_row + c
            if i >= len(prints):
                break
            x = 5 * CELL + gap + c * (thumb_w + gap)
            im = Image.open(prints[i]).convert("RGB")
            im.thumbnail((thumb_w, thumb_h))
            ox = x + (thumb_w - im.width) // 2
            oy = y0 + pad + (thumb_h - im.height) // 2
            d.rectangle([ox - CELL, oy - CELL, ox + im.width + CELL - 1, oy + im.height + CELL - 1], fill=INK)
            sheet.paste(im, (ox, oy))
            pf.draw(sheet, (x, y0 + strip_h - 10 * CELL), f"{i + 1}", 2, edge)
            pf.draw(sheet, (x + 9 * CELL, y0 + strip_h - 10 * CELL), f"> {i + 1}A", 2, edge)
            pf.draw(sheet, (x, y0 + 6 * CELL), f"K-FILM {stock.id.upper()} {stock.iso}", 2, edge)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=92)
    return out
