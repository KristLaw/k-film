"""What to dial into the 450D for each film.

These settings only change the camera's own JPEG preview: the RAW, and the
prints K-Film develops, are the same either way. They give a rough idea of
the film while you shoot (or a JPEG with the look if you shoot RAW+L).

M-Film films use M-Film's own in-camera settings (fos_film.c and
tools/genfilms.py, M-Film 0.2.1, GPL-2.0). Recipe films use the cards in
docs/RECIPES.md. Other K-Film films borrow their nearest M-Film film.

The 450D has no Kelvin white balance: 3800 K and below -> Tungsten,
anything warmer -> Daylight (Canon's Daylight is about 5200 K).
"""
from __future__ import annotations

from dataclasses import dataclass

from .films import DARKROOMS_NEAREST, Film
from .mfilm_films import FILMS as MFILM


@dataclass(frozen=True)
class CameraSettings:
    style: str              # Standard / Portrait / Landscape / Neutral / Faithful / Monochrome
    contrast: int = 0
    saturation: int = 0
    color_tone: int = 0
    sharpness: int = 3
    wb: str = "Daylight"
    shift: str = "0"        # WB shift, e.g. "A3 M1"
    htp: bool = False       # Highlight Tone Priority
    source: str = ""

    def lines(self) -> list[str]:
        mono = self.style == "Monochrome"
        ps = (f"Picture Style {self.style}: Sharpness {self.sharpness}, Contrast {self.contrast:+d}"
              + ("" if mono else f", Saturation {self.saturation:+d}, Color tone {self.color_tone:+d}"))
        wb = f"White balance {self.wb}" + (f", WB shift {self.shift}" if self.shift != "0" else "")
        out = [ps, wb]
        if self.htp:
            out.append("Highlight Tone Priority On (C.Fn), ISO 200 or more")
        return out


def _shift(gm: int, ba: int) -> str:
    parts = []
    if ba:
        parts.append(f"{'A' if ba > 0 else 'B'}{abs(ba)}")
    if gm:
        parts.append(f"{'G' if gm > 0 else 'M'}{abs(gm)}")
    return " ".join(parts) or "0"


def _wb(kelvin: int) -> str:
    return "Tungsten" if kelvin <= 3800 else "Daylight"


# M-Film's built-in eight: picstyle, contrast, saturation, color tone,
# sharpness, kelvin, G/M shift, B/A shift (fos_film.c)
_BUILTIN = {
    "portra400": ("Standard", -1, -1, 1, 2, 5500, 0, 1),
    "cinestill800t": ("Standard", 1, 1, -1, 2, 3200, 0, 0),
    "ektar100": ("Landscape", 1, 2, 0, 3, 5200, 0, 0),
    "gold200": ("Standard", 1, 1, 2, 2, 5600, 0, 2),
    "superia400": ("Standard", 1, 1, 0, 2, 5200, 1, 0),
    "velvia50": ("Landscape", 3, 4, 0, 3, 5200, 0, 0),
    "hp5": ("Monochrome", 1, 0, 0, 2, 5200, 0, 0),
    "trix400": ("Monochrome", 3, 0, 0, 2, 5200, 0, 0),
}
# the others, by kind (genfilms.py): style, contrast, saturation, color tone
_BY_KIND = {"neg": ("Standard", 0, 0, 0), "slide": ("Landscape", 2, 2, 0),
            "xpro": ("Landscape", 3, 3, 0), "bw": ("Monochrome", 1, 0, 0),
            "cine": ("Standard", 1, 1, -1), "print": ("Standard", 1, -1, 0)}

# docs/RECIPES.md cards
_RECIPES = {
    "summerchrome": CameraSettings("Neutral", -2, 2, 0, 2, "Auto", "A5 M2", True),
    "leicax": CameraSettings("Standard", 1, 1, 0, 3, "Auto", "A1"),
    "fuji200": CameraSettings("Standard", 1, 0, -1, 1, "Daylight", "A2 G1", True),
    "reggieportra": CameraSettings("Faithful", -1, 0, 1, 1, "Auto", "A3 M1"),
    "nostalgicneg": CameraSettings("Standard", -1, 1, 1, 5, "Auto", "A3 M1", True),
    "kodachrome64r": CameraSettings("Standard", 1, 1, 0, 4, "Daylight", "A4 M1"),
    "cinestill800tr": CameraSettings("Neutral", 0, 2, 0, 1, "Tungsten", "B2 G1", True),
    "pacificblues": CameraSettings("Standard", 1, 2, 0, 2, "Daylight", "A2", True),
    "portra400v2": CameraSettings("Faithful", -1, 0, 1, 1, "Daylight", "A5 G1", True),
}


def mfilm_settings(key: str) -> CameraSettings:
    if key in _BUILTIN:
        st, c, s, t, sh, k, gm, ba = _BUILTIN[key]
        return CameraSettings(st, c, s, t, sh, _wb(k), _shift(gm, ba), source="M-Film")
    f = MFILM[key]
    st, c, s, t = _BY_KIND[f["kind"]]
    return CameraSettings(st, c, s, t, 2, _wb(int(f.get("balance", 5500))), source="M-Film")


def settings(film: Film) -> CameraSettings:
    if film.engine == "mfilm":
        return mfilm_settings(film.id)
    if film.id in _RECIPES:
        return CameraSettings(**{**_RECIPES[film.id].__dict__, "source": "recipe card"})
    near = DARKROOMS_NEAREST.get(film.id)
    s = mfilm_settings(near) if near else CameraSettings("Standard")
    return CameraSettings(**{**s.__dict__, "source": f"like M-Film {near}" if near else ""})
