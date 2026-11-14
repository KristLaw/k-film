"""One shelf for every film K-Film can develop.

Two engines:
  kfilm   K-Film's own stocks and Fujifilm-recipe translations (stocks.py)
  mfilm   the 72 films of M-Film, developed with M-Film's lab model (mfilm.py)

Film ids never clash: M-Film keys are film names (portra400, cinestill800t),
K-Film ids are its own (studio400, reggieportra).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import mfilm
from .mfilm_films import FILMS as MFILM
from .stocks import STOCKS, FilmStock

# M-Film kind -> the contact sheet / shelf
_MKIND = {"neg": "color", "cine": "color", "print": "color", "xpro": "slide",
          "slide": "slide", "bw": "bw"}

# A K-Film film -> the nearest M-Film key, written into the roll log so
# Darkrooms can open the roll (it only knows M-Film films).
DARKROOMS_NEAREST = {
    "studio160": "portra160", "studio400": "portra400", "sun200": "gold200",
    "street400": "gold200", "city400": "superia400", "pastel400": "pro400h",
    "cine800t": "cinestill800t", "cine50d": "kodak2383", "vivid50": "velvia50",
    "true100": "provia100f", "chrome100": "e100gx", "grit400": "trix400",
    "soft400": "hp5", "fine100": "delta100", "red25": "panf50", "night3200": "tmax3200",
    "sepia200": "hp5", "reggieportra": "portra400", "portra400v2": "portra400",
    "fuji200": "superia200", "kodachrome64r": "kodachrome64",
    "cinestill800tr": "cinestill800t", "summerchrome": "gold200", "leicax": "ektar100",
    "nostalgicneg": "gold200", "pacificblues": "superia400",
}


@dataclass
class Film:
    id: str
    name: str
    iso: int
    kind: str              # color | slide | bw (for the sheet)
    engine: str            # kfilm | mfilm
    notes: str = ""
    shelf: str = ""
    frames: int = 36
    stock: FilmStock | None = None
    data: dict = field(default_factory=dict)

    @property
    def darkrooms_key(self) -> str | None:
        return self.id if self.engine == "mfilm" else DARKROOMS_NEAREST.get(self.id)


def _from_stock(s: FilmStock) -> Film:
    shelf = "Recipes" if "recipe" in s.tags else "K-Film"
    return Film(s.id, s.name, s.iso, s.kind, "kfilm", f"{s.notes} (inspired by {s.inspired_by})",
                shelf, s.frames, stock=s)


def _from_mfilm(key: str) -> Film:
    d = mfilm.film(key)
    lut = " · LUT" if d.get("lut") else ""
    return Film(key, d["name"], d["iso"], _MKIND.get(d["kind"], "color"), "mfilm",
                f"M-Film {d['kind']}{lut}", f"M-Film {d['kind']}", data=d)


def all_films() -> dict[str, Film]:
    out = {k: _from_stock(s) for k, s in STOCKS.items()}
    out.update({k: _from_mfilm(k) for k in MFILM})
    return out


def get(film_id: str) -> Film:
    films = all_films()
    try:
        return films[film_id.lower()]
    except KeyError:
        raise SystemExit(f"Unknown film '{film_id}'. Run `kfilm films` to see them all.") from None
