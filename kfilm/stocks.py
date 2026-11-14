"""Film stock models.

Every stock here is an original parametric model written for this project.
The ``inspired_by`` field names the real film whose general character the
model aims for; it is a description, not a claim of accuracy or affiliation.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FilmStock:
    id: str
    name: str
    kind: str                     # "color", "slide", "bw"
    iso: int
    inspired_by: str
    notes: str
    contrast: float = 1.0         # slope of the log-domain S-curve
    latitude: float = 1.0         # >1 = more stops between black and white
    # per-channel shift of the curve centre, in stops (R, G, B).
    # Positive = channel darker. Different values between channels make the
    # colour cast change from shadows to highlights, like real film crossover.
    crossover: tuple = (0.0, 0.0, 0.0)
    gain: tuple = (1.0, 1.0, 1.0)  # white-balance style multipliers (linear)
    saturation: float = 1.0
    fade: float = 0.0             # black lift (0..0.15)
    shadow_tint: tuple = (0.0, 0.0, 0.0)
    highlight_tint: tuple = (0.0, 0.0, 0.0)
    bw_mix: tuple = (0.30, 0.59, 0.11)  # channel mixer for "bw" stocks
    grain: float = 0.02           # grain strength (std-dev in display units)
    grain_size: float = 1.0       # 1 = fine, 3 = very coarse
    halation: float = 0.0         # red glow around bright highlights
    frames: int = 36
    tags: tuple = field(default_factory=tuple)


STOCKS: dict[str, FilmStock] = {}


def _add(s: FilmStock) -> None:
    STOCKS[s.id] = s


# --- colour negative -------------------------------------------------------
_add(FilmStock("studio160", "Studio 160", "color", 160, "Kodak Portra 160",
               "Soft contrast, warm natural skin, wide latitude.",
               contrast=0.85, latitude=1.25, crossover=(-0.05, 0.0, 0.08),
               gain=(1.04, 1.0, 0.95), saturation=0.92, fade=0.02,
               grain=0.012, grain_size=0.9))
_add(FilmStock("studio400", "Studio 400", "color", 400, "Kodak Portra 400",
               "Warm, gentle, forgiving. The everyday portrait stock.",
               contrast=0.9, latitude=1.2, crossover=(-0.08, 0.0, 0.1),
               gain=(1.05, 1.0, 0.94), saturation=0.95, fade=0.025,
               shadow_tint=(0.0, 0.006, 0.012), grain=0.02, grain_size=1.1))
_add(FilmStock("sun200", "Sun 200", "color", 200, "Kodak Gold 200",
               "Golden yellow cast, nostalgic holiday prints.",
               contrast=1.0, crossover=(-0.1, -0.05, 0.18),
               gain=(1.05, 1.01, 0.92), saturation=1.08, fade=0.03,
               highlight_tint=(0.02, 0.012, -0.01), grain=0.022, grain_size=1.2))
_add(FilmStock("street400", "Street 400", "color", 400, "Kodak UltraMax 400",
               "Punchy consumer film, saturated reds, warm.",
               contrast=1.1, crossover=(-0.08, 0.0, 0.06),
               gain=(1.04, 1.0, 0.94), saturation=1.15, fade=0.02,
               grain=0.028, grain_size=1.3))
_add(FilmStock("city400", "City 400", "color", 400, "Fujifilm Superia X-TRA 400",
               "Cool greens, cyan shadows, crisp.",
               contrast=1.05, crossover=(0.05, -0.04, 0.0),
               gain=(0.97, 1.02, 1.0), saturation=1.05, fade=0.02,
               shadow_tint=(-0.008, 0.01, 0.012), grain=0.026, grain_size=1.2))
_add(FilmStock("pastel400", "Pastel 400", "color", 400, "Fujifilm Pro 400H",
               "Airy pastel tones, minty greens, overexpose it.",
               contrast=0.8, latitude=1.3, crossover=(0.05, -0.05, -0.02),
               gain=(0.98, 1.02, 1.02), saturation=0.85, fade=0.04,
               highlight_tint=(-0.005, 0.01, 0.012), grain=0.018, grain_size=1.0))
_add(FilmStock("cine800t", "Cine 800T", "color", 800, "Kodak Vision3 500T / CineStill 800T",
               "Tungsten balanced: blue in daylight, red halation around lights.",
               contrast=1.0, crossover=(0.1, 0.0, -0.12),
               gain=(0.86, 0.97, 1.15), saturation=1.0, fade=0.03,
               shadow_tint=(-0.01, 0.0, 0.02), grain=0.032, grain_size=1.4,
               halation=0.55, tags=("tungsten",)))
_add(FilmStock("cine50d", "Cine 50D", "color", 50, "Kodak Vision3 50D",
               "Clean motion-picture daylight stock, low contrast, very fine.",
               contrast=0.85, latitude=1.35, crossover=(-0.03, 0.0, 0.03),
               saturation=0.95, fade=0.015, grain=0.008, grain_size=0.8,
               halation=0.15))

# --- slide -----------------------------------------------------------------
_add(FilmStock("vivid50", "Vivid 50", "slide", 50, "Fujifilm Velvia 50",
               "Huge saturation, deep blacks, landscapes. Meter for highlights.",
               contrast=1.3, latitude=0.85, crossover=(0.0, -0.03, -0.03),
               gain=(1.0, 1.01, 1.0), saturation=1.28, grain=0.008,
               grain_size=0.8, frames=36))
_add(FilmStock("true100", "True 100", "slide", 100, "Fujifilm Provia 100F",
               "Neutral, accurate slide film.",
               contrast=1.25, latitude=0.85, saturation=1.15, grain=0.009,
               grain_size=0.8))
_add(FilmStock("chrome100", "Chrome 100", "slide", 100, "Kodak Ektachrome E100",
               "Clean slide film with cool blue skies.",
               contrast=1.25, latitude=0.85, crossover=(0.03, 0.0, -0.05),
               gain=(0.98, 1.0, 1.04), saturation=1.2, grain=0.01, grain_size=0.8))

# --- black and white -------------------------------------------------------
_add(FilmStock("grit400", "Grit 400", "bw", 400, "Kodak Tri-X 400",
               "Classic gritty reportage contrast.",
               contrast=1.3, bw_mix=(0.3, 0.55, 0.15), grain=0.045,
               grain_size=1.5, fade=0.01))
_add(FilmStock("soft400", "Soft 400", "bw", 400, "Ilford HP5 Plus",
               "Softer, flexible, pushes well.",
               contrast=1.05, latitude=1.15, bw_mix=(0.3, 0.55, 0.15),
               grain=0.035, grain_size=1.3, fade=0.02))
_add(FilmStock("fine100", "Fine 100", "bw", 100, "Ilford Delta 100 / Fuji Acros",
               "Very fine grain, smooth tones, deep blacks.",
               contrast=1.15, bw_mix=(0.25, 0.6, 0.15), grain=0.012,
               grain_size=0.8))
_add(FilmStock("red25", "Red Filter 25", "bw", 25, "Pan F + red filter",
               "Dark dramatic skies, bright skin. Slow and sharp.",
               contrast=1.35, bw_mix=(0.75, 0.25, 0.0), grain=0.008,
               grain_size=0.7))
_add(FilmStock("night3200", "Night 3200", "bw", 3200, "Kodak T-Max P3200",
               "Push-processed night film: big grain, punchy.",
               contrast=1.25, latitude=0.95, bw_mix=(0.33, 0.5, 0.17),
               grain=0.075, grain_size=2.2, fade=0.03))
_add(FilmStock("sepia200", "Sepia 200", "bw", 200, "Toned fibre prints",
               "Warm-toned B&W print look.",
               contrast=1.0, bw_mix=(0.3, 0.59, 0.11), grain=0.025,
               shadow_tint=(0.015, 0.005, -0.01),
               highlight_tint=(0.035, 0.015, -0.025), fade=0.04))


# --- community recipes -----------------------------------------------------
# Translations of popular Fujifilm JPEG "recipes" into this darkroom's
# parameters. The original settings and sources are in docs/RECIPES.md.
# They are approximations made by eye, not measured matches.
_add(FilmStock("summerchrome", "Summer Chrome", "color", 400,
               "Summer Chrome recipe by Osan Bilgi (Classic Chrome base)",
               "Warm, golden, cinematic. Flat highlights and shadows, strong grain.",
               contrast=0.82, latitude=1.3, crossover=(-0.08, 0.0, 0.1),
               gain=(1.10, 1.0, 0.86), saturation=1.08, fade=0.03,
               shadow_tint=(-0.004, 0.004, 0.01), highlight_tint=(0.02, 0.01, -0.015),
               grain=0.035, grain_size=1.6, halation=0.1, tags=("recipe",)))
_add(FilmStock("leicax", "Leica X", "color", 200,
               "Leica X recipe by Carl Cruz (Classic Chrome base)",
               "Crisp, clean, bold colour with cool shadows. Almost no grain.",
               contrast=1.08, latitude=1.0, crossover=(0.02, 0.0, -0.03),
               gain=(1.02, 1.0, 0.97), saturation=1.1, fade=0.0,
               shadow_tint=(-0.006, 0.0, 0.01), grain=0.006, grain_size=0.8,
               tags=("recipe",)))
_add(FilmStock("fuji200", "Fuji 200", "color", 200,
               "Fujicolor C200 recipe by Fuji X Weekly (Classic Negative base)",
               "Cheap-and-cheerful Fuji film: green-cyan shadows, crunchy contrast.",
               contrast=1.05, latitude=1.2, crossover=(0.06, -0.03, -0.02),
               gain=(1.0, 1.0, 0.95), saturation=1.0, fade=0.02,
               shadow_tint=(-0.008, 0.008, 0.004), highlight_tint=(0.012, 0.0, 0.004),
               grain=0.022, grain_size=1.5, tags=("recipe",)))
_add(FilmStock("reggieportra", "Reggie's Portra", "color", 400,
               "Reggie's Portra recipe by Reggie Ballesteros (Classic Chrome base)",
               "Warm Portra-style skin, soft highlights, gentle fade.",
               contrast=0.88, latitude=1.15, crossover=(-0.06, 0.0, 0.08),
               gain=(1.05, 1.0, 0.92), saturation=1.0, fade=0.02,
               highlight_tint=(0.01, 0.005, -0.005), grain=0.016, grain_size=1.0,
               tags=("recipe",)))
_add(FilmStock("nostalgicneg", "Nostalgic Neg", "color", 400,
               "Fujifilm Nostalgic Neg. + AV Americana recipe by AV Schofield",
               "1970s American colour prints: amber highlights, rich shadows, gritty.",
               contrast=0.95, latitude=1.2, crossover=(-0.06, -0.02, 0.1),
               gain=(1.05, 1.0, 0.94), saturation=1.05, fade=0.02,
               highlight_tint=(0.03, 0.015, -0.02), grain=0.018, grain_size=1.0,
               tags=("recipe",)))


_add(FilmStock("kodachrome64r", "Kodachrome 64 (recipe)", "color", 64,
               "Kodachrome 64 recipe by Fuji X Weekly (Classic Chrome base)",
               "Punchy, warm, deep shadows and bold reds. Sharp, little grain.",
               contrast=1.12, latitude=1.0, crossover=(-0.04, 0.0, 0.06),
               gain=(1.05, 1.0, 0.9), saturation=1.08, fade=0.0,
               grain=0.012, grain_size=0.9, tags=("recipe",)))
_add(FilmStock("cinestill800tr", "CineStill 800T (recipe)", "color", 800,
               "CineStill 800T recipe by Fuji X Weekly (Eterna base)",
               "Cool teal night look, glowing lights, big grain. For city nights.",
               contrast=0.95, latitude=1.2, crossover=(0.08, 0.0, -0.06),
               gain=(0.9, 1.0, 1.06), saturation=1.05, fade=0.03,
               shadow_tint=(-0.008, 0.004, 0.012), grain=0.034, grain_size=1.6,
               halation=0.5, tags=("recipe", "tungsten")))
_add(FilmStock("pacificblues", "Pacific Blues", "color", 400,
               "Pacific Blues recipe by Fuji X Weekly (Classic Negative base)",
               "Deep blue sea and sky, warm skin, strong grain. Made for beach days.",
               contrast=1.05, latitude=1.25, crossover=(0.04, -0.02, -0.06),
               gain=(1.02, 1.0, 0.96), saturation=1.15, fade=0.02,
               shadow_tint=(-0.01, 0.0, 0.015), grain=0.032, grain_size=1.6,
               tags=("recipe",)))
_add(FilmStock("portra400v2", "Portra 400 v2", "color", 400,
               "Kodak Portra 400 v2 recipe by Fuji X Weekly (Classic Chrome base)",
               "Warm Portra leaning yellow-green, soft shadows, visible grain.",
               contrast=0.88, latitude=1.2, crossover=(-0.04, -0.02, 0.1),
               gain=(1.03, 1.01, 0.88), saturation=0.98, fade=0.025,
               highlight_tint=(0.01, 0.012, -0.008), grain=0.026, grain_size=1.0,
               tags=("recipe",)))


def get(stock_id: str) -> FilmStock:
    try:
        return STOCKS[stock_id.lower()]
    except KeyError:
        raise KeyError(f"unknown stock '{stock_id}'. Run `kfilm films` to list them.") from None
