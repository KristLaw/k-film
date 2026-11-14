"""Contact sheets that look like a strip of developed negatives."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont



def _font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1
        return ImageFont.load_default()


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
    thumb_h = int(thumb_w * 2 / 3)          # 3:2 like the 450D and 35 mm
    gap = 14
    strip_pad = 44                           # room for sprockets + edge print
    rows = max(1, (len(prints) + per_row - 1) // per_row)
    strip_h = thumb_h + strip_pad * 2
    W = per_row * (thumb_w + gap) + gap + 40
    H = rows * (strip_h + 24) + 90
    sheet = Image.new("RGB", (W, H), (236, 233, 226))
    d = ImageDraw.Draw(sheet)
    edge = (226, 140, 50) if stock.kind != "bw" else (210, 210, 200)
    f_small, f_title = _font(15), _font(26)

    d.text((20, 22), f"{stock.name}  ·  ISO {stock.iso}  ·  {len(prints)} frames  ·  Canon EOS 450D",
           fill=(40, 40, 40), font=f_title)

    for r in range(rows):
        y0 = 70 + r * (strip_h + 24)
        d.rectangle([20, y0, W - 20, y0 + strip_h], fill=(18, 16, 14))
        for sx in range(30, W - 30, 22):    # sprocket holes
            for sy in (y0 + 8, y0 + strip_h - 20):
                d.rounded_rectangle([sx, sy, sx + 11, sy + 12], 2, fill=(236, 233, 226))
        for c in range(per_row):
            i = r * per_row + c
            if i >= len(prints):
                break
            x = 20 + gap + c * (thumb_w + gap)
            im = Image.open(prints[i]).convert("RGB")
            im.thumbnail((thumb_w, thumb_h))
            ox = x + (thumb_w - im.width) // 2
            oy = y0 + strip_pad + (thumb_h - im.height) // 2
            sheet.paste(im, (ox, oy))
            d.text((x + 4, y0 + strip_h - 40), f"{i + 1}", fill=edge, font=f_small)
            d.text((x + 36, y0 + strip_h - 40), f"> {i + 1}A", fill=edge, font=f_small)
            d.text((x + 4, y0 + 23), f"{stock.id.upper()} {stock.iso}", fill=edge, font=f_small)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=90)
    return out
