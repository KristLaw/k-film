"""The K-Film card folder: what goes on the 450D's SD card, like M-Film's zip.

A 450D can't run anything from the card, so the folder holds no program.
It carries the film shelf (a pixel box for every film), the 450D settings
for each film and a short guide, and K-Film keeps the roll in it:

    KFILM/
      README.TXT      how to shoot a roll
      FILMS.TXT       every film: ISO and what to set on the 450D
      VERSION.TXT
      SHELF.PNG       all the films on one page
      SHELF/<id>.PNG  one film box per film
      ROLL.JSON       the loaded roll (written by `kfilm load`)

The camera ignores this folder: it only reads DCIM and MISC.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

from . import __version__
from . import pixelfont as pf
from .camera450d import settings
from .contact import AMBER, AMBER_DARK, CREAM, INK, MUTED
from .films import Film, all_films

# box colours by shelf: (body, band)
_BOX = {"color": ((232, 150, 40), (120, 30, 20)), "slide": ((40, 110, 200), (230, 230, 220)),
        "bw": ((60, 60, 60), (230, 230, 220))}
_RECIPE = ((150, 60, 170), (255, 210, 90))


def _iso_on_450d(iso: int) -> str:
    return "100" if iso < 100 else "3200 (H)" if iso > 1600 else str(iso)


_SHORT = {"fujifilm": "FUJI", "fujichrome": "FUJI", "fujicolor": "FUJI", "lomography": "LOMO",
          "cinestill": "CINE", "kodak": "KODAK", "ilford": "ILFORD", "agfa": "AGFA", "rollei": "ROLLEI"}


def _brand(f: Film) -> str:
    if f.engine == "kfilm":
        return "RECIPE" if f.shelf == "Recipes" else "K-FILM"
    first = f.name.split(" ")[0].lower()
    return _SHORT.get(first, first.upper()[:6])


def film_box(f: Film, scale: int = 6) -> Image.Image:
    """A pixel film box, 44 x 56 cells, drawn big with hard edges."""
    w, h = 44, 56
    im = Image.new("RGB", (w, h), INK)
    d = ImageDraw.Draw(im)
    body, band = _RECIPE if f.shelf == "Recipes" else _BOX.get(f.kind, _BOX["color"])
    d.rectangle([2, 3, 41, 52], fill=body)
    d.rectangle([2, 20, 41, 33], fill=band)
    d.rectangle([2, 3, 41, 5], fill=AMBER_DARK if f.kind != "bw" else MUTED)
    on_body = CREAM if sum(body) < 450 else INK
    on_band = INK if sum(band) > 450 else CREAM

    def centre(text, y, colour):
        pf.draw(im, ((w - pf.width(text, 1)) // 2, y), text, 1, colour)

    centre(_brand(f), 9, on_body)
    centre(str(f.iso), 23, on_band)
    centre("K-FILM", 42, on_body)
    return im.resize((w * scale, h * scale), Image.NEAREST)


def shelf_page(films: list[Film], per_row: int = 10) -> Image.Image:
    bw, bh, lab = 132, 168, 34
    rows = (len(films) + per_row - 1) // per_row
    page = Image.new("RGB", (per_row * (bw + 16) + 16, rows * (bh + lab + 10) + 90), INK)
    pf.draw(page, (16, 16), "K-FILM SHELF", 5, AMBER, shadow=AMBER_DARK)
    pf.draw(page, (16, 60), f"{len(films)} FILMS FOR THE CANON EOS 450D", 2, MUTED)
    for i, f in enumerate(films):
        x, y = 16 + (i % per_row) * (bw + 16), 90 + (i // per_row) * (bh + lab + 10)
        page.paste(film_box(f, 3), (x, y))
        pf.draw(page, (x, y + bh + 4), f.id[:14], 1, CREAM)
        pf.draw(page, (x, y + bh + 16), f"ISO {_iso_on_450d(f.iso)}", 1, MUTED)
    return page


def films_text(films: list[Film]) -> str:
    out = [f"K-FILM {__version__} · films for the Canon EOS 450D", "",
           "Load one with:  kfilm load <id>", "Shoot RAW, Review time Off, at the ISO below.",
           "Picture Style / WB only change the camera's preview JPEG, not the RAW.", ""]
    shelf = None
    for f in films:
        if f.shelf != shelf:
            shelf = f.shelf
            out += ["", f"== {shelf} ==", ""]
        s = settings(f)
        out.append(f"{f.id:<16} {f.name}")
        out.append(f"{'':<16} ISO {_iso_on_450d(f.iso)} · " + " · ".join(s.lines()))
    return "\n".join(out) + "\n"


README = """K-FILM for the Canon EOS 450D
=============================

Shoot your 450D like a film camera. Nothing here runs in the camera: the
450D can't run programs from the card, and K-Film never changes it. The
camera shoots RAW; K-Film on your computer keeps the roll and develops it.

Do NOT copy an M-Film camera zip (autoexec.bin, ML-SETUP.FIR) onto this
card: those are built for other cameras.

1. Format the card in the 450D (MENU > Format). Formatting erases this
   folder too: copy it back after, or let `kfilm load` make it again.
2. On the computer:  kfilm load portra400 --frames 24
   (see FILMS.TXT or SHELF.PNG for every film)
3. On the 450D: Quality RAW, Review time Off, the ISO K-Film says.
   Optional: the Picture Style and WB in FILMS.TXT, for the preview.
4. Shoot the roll without looking at the photos.
5. Card in the computer:  kfilm status   (then Darkrooms can open it)
                          kfilm develop  (prints + contact sheet, here in
                                          KFILM/PRINTS)

Get K-Film: https://github.com/KristLaw/k-film
"""


def build(dest: Path) -> Path:
    """Write the KFILM folder's guide and shelf into dest (a card root or
    any folder). The roll files already there are left alone."""
    films = sorted(all_films().values(), key=lambda f: (
        ["Recipes", "K-Film"].index(f.shelf) if f.shelf in ("Recipes", "K-Film") else 2, f.shelf, f.iso, f.id))
    k = Path(dest) / "KFILM"
    (k / "SHELF").mkdir(parents=True, exist_ok=True)
    (k / "README.TXT").write_text(README.replace("\n", "\r\n"), encoding="ascii", newline="")
    (k / "FILMS.TXT").write_text(films_text(films).replace("\n", "\r\n"), encoding="utf-8", newline="")
    (k / "VERSION.TXT").write_text(f"K-Film {__version__}\r\n", newline="")
    for f in films:
        film_box(f, 4).save(k / "SHELF" / f"{f.id.upper()}.PNG", optimize=True)
    shelf_page(films).save(k / "SHELF.PNG", optimize=True)
    return k


def build_zip(out: Path, tmp: Path) -> Path:
    """K-Film-card-450D.zip: the folder, ready to unzip onto a card."""
    k = build(tmp)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(k.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(tmp).as_posix())
    return Path(out)
