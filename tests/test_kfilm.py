"""K-Film 0.2: the M-Film engine, the film shelf and Darkrooms roll logs."""
import json

import numpy as np
from PIL import Image

from kfilm import cli, darkrooms, mfilm
from kfilm.films import DARKROOMS_NEAREST, all_films
from kfilm.mfilm_films import FILMS as MFILM
from kfilm.roll import Roll


def _shot(folder, n, when="2026:11:14 16:16:48"):
    folder.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", (120, 80), (120, 140, 160))
    ex = Image.Exif()
    ex[0x0132] = when
    im.save(folder / f"IMG_{n:04d}.JPG", exif=ex)


def test_shelf_has_every_film():
    films = all_films()
    assert len(MFILM) == 72
    assert len(films) == len(MFILM) + 26
    for k in DARKROOMS_NEAREST:
        assert k in films, k
        assert DARKROOMS_NEAREST[k] in MFILM, k


def test_mfilm_model_prints_grey_as_grey_ish():
    grey = np.full((16, 24, 3), 0.18, np.float32)
    for k in MFILM:
        f = dict(mfilm.film(k), grain=0, halation=0)
        y = mfilm.develop(grey, f, use_lut=False)
        assert 0.2 < y.mean() < 0.8, k
        if f.get("mono"):
            assert np.allclose(y[..., 0], y[..., 2])


def test_curve_is_monotonic():
    x = np.geomspace(1e-4, 8, 200)
    for k, f in MFILM.items():
        for c in range(len(f["contrast"])):
            y = mfilm.curve(x, f["contrast"][c], f["pivot"][c], f["black"][c], f["white"][c])
            assert np.all(np.diff(y) >= -1e-9), k


def test_tungsten_film_turns_daylight_blue():
    b = mfilm.balance(3200)
    assert b[2] > b[1] > b[0]


def test_darkrooms_log(tmp_path):
    card = tmp_path
    cli.main(["load", "portra400", "--card", str(card), "--frames", "12"])
    for n in (1, 2, 3):
        _shot(card / "DCIM" / "100CANON", n)
    cli.main(["status", "--card", str(card)])
    log = (card / "DCIM" / "100CANON" / "ROLL_001.TXT").read_text()
    lines = log.splitlines()
    assert lines[0] == darkrooms.HEADER
    assert "roll = 001" in lines and "film = portra400" in lines and "exposures = 12" in lines
    assert lines[-1].startswith("3  IMG_0003.JPG  2026-11-14 16:16:48")
    cli.main(["rewind", "--card", str(card)])
    log = (card / "DCIM" / "100CANON" / "ROLL_001.TXT").read_text()
    assert "# rewound" in log and "after 3 of 12 frames" in log


def test_kfilm_recipe_maps_to_mfilm_key(tmp_path):
    cli.main(["load", "reggieportra", "--card", str(tmp_path)])
    assert Roll.load(tmp_path).darkrooms == "portra400"


def test_legacy_xsiroll_card_still_works(tmp_path):
    old = tmp_path / "XSIROLL"
    old.mkdir()
    (old / "ROLL.JSON").write_text(json.dumps({"stock": "studio400", "frames": 24, "existing": []}))
    _shot(tmp_path / "DCIM" / "100CANON", 1)
    r = Roll.load(tmp_path)
    assert r.stock == "studio400" and len(r.shots(tmp_path)) == 1


def test_mfilm_roll_develops(tmp_path):
    cli.main(["load", "trix400", "--card", str(tmp_path), "--frames", "12"])
    for n in (1, 2):
        _shot(tmp_path / "DCIM" / "100CANON", n)
    cli.main(["develop", "--card", str(tmp_path), "--size", "screen"])
    out = list((tmp_path / "KFILM" / "PRINTS").rglob("*.jpg"))
    assert len(out) == 3


def test_every_film_has_450d_settings():
    from kfilm.camera450d import settings
    for f in all_films().values():
        s = settings(f)
        assert s.style in {"Standard", "Portrait", "Landscape", "Neutral", "Faithful", "Monochrome"}, f.id
        assert s.wb in {"Auto", "Daylight", "Tungsten"}, f.id       # no Kelvin on a 450D
        assert -4 <= s.contrast <= 4 and 0 <= s.sharpness <= 7, f.id
    assert settings(all_films()["cinestill800t"]).wb == "Tungsten"


def test_pixel_font_and_sheet(tmp_path):
    from kfilm import pixelfont as pf
    assert all(len(g) == 35 for g in pf._G.values())
    im = Image.new("RGB", (200, 20))
    assert pf.draw(im, (0, 0), "K-FILM", 2) == pf.width("K-FILM", 2) + 2
    assert im.getbbox() is not None


def test_card_folder_keeps_the_roll(tmp_path):
    cli.main(["load", "portra400", "--card", str(tmp_path)])
    roll = (tmp_path / "KFILM" / "ROLL.JSON").read_text()
    cli.main(["card", "--card", str(tmp_path), "--samples", str(tmp_path / "none")])
    k = tmp_path / "KFILM"
    assert (k / "ROLL.JSON").read_text() == roll
    assert (k / "README.TXT").exists() and (k / "SHELF.PNG").exists()
    assert len(list((k / "SHELF").glob("*.PNG"))) == len(all_films())
    assert "portra400" in (k / "FILMS.TXT").read_text()
    _shot(tmp_path / "DCIM" / "100CANON", 1)
    assert len(Roll.load(tmp_path).shots(tmp_path)) == 1          # shelf PNGs aren't frames


def test_camera_shelf_pages_are_canon_dcf(tmp_path):
    from kfilm.cardkit import build
    from PIL import ExifTags
    build(tmp_path, samples=tmp_path / "none")
    pages = sorted((tmp_path / "DCIM" / "100CANON").glob("KFLM*.JPG"))
    assert len(pages) == len(all_films()) + 1 and pages[0].name == "KFLM0001.JPG"
    data = pages[1].read_bytes()
    assert data[:4] == b"\xff\xd8\xff\xe1" and data[6:10] == b"Exif"      # Exif first, no JFIF
    im = Image.open(pages[1])
    assert im.size == (2256, 1504) and im.getexif()[0x0110] == "Canon EOS 450D"
    assert im.getexif().get_ifd(ExifTags.IFD.IFD1)[0x0202] > 0                # 160x120 thumbnail
    cli.main(["load", "portra400", "--card", str(tmp_path)])
    assert Roll.load(tmp_path).shots(tmp_path) == []                          # shelf isn't a roll
