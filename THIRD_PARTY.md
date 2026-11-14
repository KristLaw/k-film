# Third-party code and data

- **M-Film** by HNGSeries (GPL-2.0), https://github.com/HNGSeries/mfilm-canon-film-simulation
  - `kfilm/mfilm_films.py`, `kfilm/mfilm_filmluts.py`: the film list (`ml-dev/films/films.py`,
    `filmluts.py`, v0.2.1), copied with its numbers unchanged.
  - `kfilm/lut.py`: the `.cube` reader and log encodings (`ml-dev/films/lut.py`).
  - `kfilm/mfilm.py`: a numpy port of the film model and print steps in `ml-dev/filmos/fos_dev.c`.
  - `kfilm/darkrooms.py`: writes the roll log format of `ml-dev/fork/src/filmroll.c`.
  K-Film is GPL-2.0 for this reason.
- **Film-Luts** by Yahia Angelo (MIT), https://github.com/YahiaAngelo/Film-Luts: the colour
  LUTs of 63 films. Not in this repository; `kfilm getluts` downloads them with their licence.
- **LibRaw** / **rawpy**: RAW decoding (installed as a dependency).
- Recipe settings in `docs/RECIPES.md` belong to their creators, credited there.
