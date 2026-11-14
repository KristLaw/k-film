"""Rebuild the README pictures in K-Film's pixel style.

    python tools/make_images.py        # -> docs/img/*.png / *.jpg

Uses the made-up test chart in docs/img/stocks_demo.jpg, never real photos.
Set KFILM_LUTS (or run `kfilm getluts`) for the M-Film LUT films' colours.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from kfilm import mfilm, pixelfont as pf               # noqa: E402
from kfilm.contact import AMBER, CREAM, INK, contact_sheet  # noqa: E402
from kfilm.films import get                            # noqa: E402
from kfilm.process import develop, srgb_to_linear, to_image  # noqa: E402

IMG = ROOT / "docs" / "img"
CHART = Image.open(IMG / "stocks_demo.jpg").convert("RGB")


def chart_crop(i, size=(360, 240)):
    w, h = CHART.size
    c = CHART.crop(((i % 3) * w // 3, (i // 3 % 2) * h // 2, (i % 3 + 1) * w // 3, (i // 3 % 2 + 1) * h // 2))
    return srgb_to_linear(np.asarray(c.resize(size), np.float32) / 255)


def print_of(film_id, lin, seed=1):
    f = get(film_id)
    y = (develop(lin, f.stock, seed=seed, grain_scale=0.1) if f.engine == "kfilm"
         else mfilm.develop(lin, f.data, seed=seed, scale=0.1))
    return to_image(y)


def banner():
    """Pixel-art banner: the KARAFILM name and four canisters on the shelf."""
    from kfilm import art
    w, h, s = 480, 104, 3
    im = Image.new("RGB", (w, h), art.BG)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 92, w, h], fill=art.BG_DARK)
    pf.draw(im, (14, 14), art.BRAND, 4, art.OUTLINE)
    pf.draw(im, (16, 48), "SHOOT YOUR CANON 450D LIKE FILM", 1, (70, 70, 76))
    pf.draw(im, (16, 58), "98 FILMS · RECIPES · M-FILM", 1, (110, 60, 170))
    picks = ["reggieportra", "portra400", "velvia50", "trix400"]
    for i, fid in enumerate(picks):
        can = art.canister(get(fid), leader=(i == len(picks) - 1))
        d.rectangle([236 + i * 50, 96, 282 + i * 50, 99], fill=(160, 160, 168))
        im.paste(can, (230 + i * 50, 8), can)
    im.resize((w * s, h * s), Image.NEAREST).save(IMG / "kfilm_banner.png")


def film_grid():
    ids = ["portra400", "cinestill800t", "kodachrome64", "ektar100", "kodak2383", "trix400",
           "pacificblues", "reggieportra", "summerchrome"]
    tw, th, lab = 360, 240, 36
    out = Image.new("RGB", (tw * 3 + 16, (th + lab) * 3 + 12), INK)
    for k, fid in enumerate(ids):
        x, y = 8 + (k % 3) * tw, 6 + (k // 3) * (th + lab)
        tile = print_of(fid, chart_crop(k % 6))
        out.paste(tile.resize((tw - 8, th - 8)), (x + 4, y + 4))
        pf.draw(out, (x + 6, y + th + 6), get(fid).name, 2, CREAM)
        pf.draw(out, (x + 6, y + th + 22), fid, 1, AMBER)
    out.save(IMG / "mfilm_demo.jpg", quality=90)


def sheet():
    tmp = IMG / "_tmp"
    tmp.mkdir(exist_ok=True)
    ps = []
    for i in range(6):
        p = tmp / f"{i}.jpg"
        print_of("portra400", chart_crop(i, (450, 300)), seed=i).save(p)
        ps.append(p)
    contact_sheet(ps, get("portra400"), IMG / "contact_sheet_demo.jpg")
    for p in ps:
        p.unlink()
    tmp.rmdir()


if __name__ == "__main__":
    banner()
    film_grid()
    sheet()
    print("docs/img updated")
