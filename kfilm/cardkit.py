"""The Karafilm card folder: what goes on the 450D's SD card, like M-Film's zip.

A 450D can't run anything from the card, so there is no program. Instead:

    DCIM/100CANON/KFLM0001.JPG ... KFLM0099.JPG
        the CAMERA SHELF: one pixel-art page per film that the 450D shows
        in Playback (press PLAY, turn the dial). Cover first, then every film.
    KFILM/
      README.TXT      how to shoot a roll
      FILMS.TXT       every film: ISO and what to set on the 450D
      VERSION.TXT
      SHELF.PNG       all the films on one page
      SHELF/<ID>.PNG  one canister per film
      ROLL.JSON       the loaded roll (written by `kfilm load`)

Shelf pages use the DCF names KFLM0001-0099: low numbers, so the camera's
own file numbering carries on after your photos, and K-Film never counts
them as frames of a roll.
"""
from __future__ import annotations

import glob
import zipfile
from pathlib import Path

from PIL import Image

from . import __version__, art
from . import pixelfont as pf
from .camera450d import _BUILTIN, settings
from .dcf import save_dcf
from .films import DARKROOMS_NEAREST, Film, all_films
from .mfilm_films import FILMS as MFILM

SHELF_PREFIX = "KFLM"
SHELF_FOLDER = "100CANON"
CHART = Path(__file__).resolve().parent / "data" / "chart.jpg"


def is_shelf_page(p: Path) -> bool:
    return p.name.upper().startswith(SHELF_PREFIX) and p.suffix.upper() == ".JPG"


def _iso_on_450d(iso: int) -> str:
    if iso < 100:
        import math
        return f"ISO 100 +{math.log2(100 / iso):.0f}EV"
    return "ISO 3200 (H)" if iso > 1600 else f"ISO {iso}"


def shelf_order() -> list[Film]:
    films = all_films().values()
    rank = {"Recipes": 0, "K-Film": 1}
    return sorted(films, key=lambda f: (rank.get(f.shelf, 2), f.shelf, f.iso, f.id))


# ---------------------------------------------------------------- samples
def find_samples() -> Path | None:
    """M-Film's sample prints (ML/SAMPLES/Fnnn.BMP) from an M-Film camera
    folder, if one is on this computer."""
    for pat in ("/Applications/M-Film-camera-*/ML/SAMPLES", str(Path.home() / "*/M-Film-camera-*/ML/SAMPLES"),
                str(Path.home() / "Downloads/M-Film-camera-*/ML/SAMPLES")):
        for hit in sorted(glob.glob(pat)):
            if Path(hit, "F000.BMP").is_file():
                return Path(hit)
    return None


def _mfilm_index() -> dict[str, int]:
    order = list(_BUILTIN) + [k for k in MFILM if k not in _BUILTIN]
    return {k: i for i, k in enumerate(order)}


def sample_for(f: Film, samples: Path | None) -> Image.Image:
    """The film's sample print: M-Film's own for its films; for K-Film's,
    developed from the test chart."""
    if samples is not None and f.engine == "mfilm":
        im = art.load_sample(samples / f"F{_mfilm_index()[f.id]:03d}.BMP")
        if im is not None:
            return im
    return art.chart_sample(f, CHART)


# ---------------------------------------------------------------- pieces
def films_text(films: list[Film]) -> str:
    out = [f"KARAFILM {__version__} · films for the Canon EOS 450D", "",
           "Load one with:  kfilm load <id>", "Shoot RAW, Review time Off, at the ISO below.",
           "Picture Style / WB only change the camera's preview JPEG, not the RAW.", ""]
    shelf = None
    for f in films:
        if f.shelf != shelf:
            shelf = f.shelf
            out += ["", f"== {shelf} ==", ""]
        s = settings(f)
        out.append(f"{f.id:<16} {f.name}")
        out.append(f"{'':<16} {_iso_on_450d(f.iso)} · " + " · ".join(s.lines()))
    return "\n".join(out) + "\n"


def shelf_sheet(films: list[Film], per_row: int = 10) -> Image.Image:
    cw, ch = 96, 92
    rows = (len(films) + per_row - 1) // per_row
    im = Image.new("RGB", (per_row * (cw + 8) + 16, rows * (ch + 22) + 44), art.BG)
    pf.draw(im, (10, 8), f"{art.BRAND} SHELF", 2, art.OUTLINE)
    pf.draw(im, (10, 26), f"{len(films)} FILMS FOR THE CANON EOS 450D", 1, (90, 90, 96))
    for i, f in enumerate(films):
        x, y = 10 + (i % per_row) * (cw + 8), 40 + (i // per_row) * (ch + 22)
        can = art.canister(f)
        im.paste(can, (x, y), can)
        pf.draw(im, (x + 2, y + ch + 3), f.id[:15].upper(), 1, art.INK)
    return im.resize((im.width * 3, im.height * 3), Image.NEAREST)


README = """KARAFILM for the Canon EOS 450D
===============================

Shoot your 450D like a film camera. Nothing here runs in the camera: the
450D can't run programs from the card, and Karafilm never changes it.
The camera shoots RAW; Karafilm (the `kfilm` command) keeps the roll and
develops it on your computer.

THE SHELF ON THE CAMERA: press PLAY and turn the dial. The KFLM pages
in DCIM/100CANON show every film, its sample and its 450D settings.

Do NOT copy an M-Film camera zip (autoexec.bin, ML-SETUP.FIR) onto this
card: those are built for other cameras.

1. Format the card in the 450D (MENU > Format). That erases the shelf too:
   put it back with  kfilm card
2. On the computer:  kfilm load portra400 --frames 24
3. On the 450D: Quality RAW, Review time Off, the ISO Karafilm says.
   Optional: the Picture Style and WB from the shelf page, for the preview.
4. Shoot the roll without looking at the photos.
5. Card in the computer:  kfilm status   (then Darkrooms can open it)
                          kfilm develop  (prints + contact sheet)

Get it: https://github.com/KristLaw/k-film
"""


# ---------------------------------------------------------------- build
def build(dest: Path, camera_shelf: bool = True, samples: Path | None = None) -> Path:
    """Write the KFILM folder and the camera shelf into dest (a card root
    or any folder). Roll files already there are left alone."""
    films = shelf_order()
    k = Path(dest) / "KFILM"
    (k / "SHELF").mkdir(parents=True, exist_ok=True)
    for old in (k / "SHELF").glob("*.PNG"):
        old.unlink()
    (k / "README.TXT").write_text(README.replace("\n", "\r\n"), encoding="ascii", newline="")
    (k / "FILMS.TXT").write_text(films_text(films).replace("\n", "\r\n"), encoding="utf-8", newline="")
    (k / "VERSION.TXT").write_text(f"Karafilm (K-Film) {__version__}\r\n", newline="")
    for f in films:
        art.canister(f, 4).save(k / "SHELF" / f"{f.id.upper()}.PNG", optimize=True)
    shelf_sheet(films).save(k / "SHELF.PNG", optimize=True)
    if camera_shelf:
        write_camera_shelf(Path(dest), films, samples if samples is not None else find_samples())
    return k


def write_camera_shelf(card: Path, films: list[Film], samples: Path | None) -> list[Path]:
    folder = card / "DCIM" / SHELF_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob(f"{SHELF_PREFIX}*.JPG"):
        old.unlink()
    total = len(films) + 1
    out = [save_dcf(art.cover(films, len(films)), folder / f"{SHELF_PREFIX}0001.JPG")]
    for i, f in enumerate(films, 2):
        page = art.page(f, settings(f), sample_for(f, samples), i, total, _iso_on_450d(f.iso))
        out.append(save_dcf(page, folder / f"{SHELF_PREFIX}{i:04d}.JPG"))
    return out


def build_zip(out: Path, tmp: Path) -> Path:
    """K-Film-card-450D.zip: the folder and camera shelf, ready to unzip
    onto a card. Uses the test chart for samples (M-Film's sample photos
    aren't ours to ship)."""
    build(tmp, samples=Path("/nonexistent"))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(Path(tmp).rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(tmp).as_posix())
    return Path(out)
