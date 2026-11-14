import dataclasses
import shutil

import numpy as np
import pytest
from PIL import Image

from kfilm import cli
from kfilm.hald import HaldCLUT, identity_hald
from kfilm.process import develop, film_curve
from kfilm.roll import Roll
from kfilm.stocks import STOCKS


def _shot(folder, n, color=(120, 140, 160)):
    folder.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (120, 80), color).save(folder / f"IMG_{n:04d}.JPG")


@pytest.fixture
def card(tmp_path):
    _shot(tmp_path / "DCIM" / "100CANON", 1)          # old photo already on card
    return tmp_path


def test_grey_prints_mid_grey():
    for s in STOCKS.values():
        y = develop(np.full((8, 8, 3), 0.18, np.float32), dataclasses.replace(s, grain=0))
        assert 0.3 < y.mean() < 0.6, s.id


def test_curve_monotonic():
    x = np.geomspace(1e-4, 8, 200).astype(np.float32)
    for s in STOCKS.values():
        y = film_curve(x, s.contrast, s.latitude)
        assert np.all(np.diff(y) >= -1e-6), s.id


def test_bw_is_neutral():
    rgb = np.random.default_rng(1).random((16, 16, 3)).astype(np.float32)
    y = develop(rgb, dataclasses.replace(STOCKS["fine100"], grain=0))
    assert np.allclose(y[..., 0], y[..., 1], atol=1e-5)


def test_identity_hald_is_identity(tmp_path):
    lut_path = tmp_path / "_id_hald.png"
    identity_hald(8).save(lut_path)
    lut = HaldCLUT(lut_path)
    y = np.random.default_rng(2).random((10, 10, 3)).astype(np.float32)
    assert np.abs(lut.apply(y) - y).max() < 0.01


def test_roll_workflow(card, capsys):
    cli.main(["load", "studio400", "--card", str(card), "--frames", "12"])
    for n in range(2, 6):                                 # shoot 4 frames
        _shot(card / "DCIM" / "100CANON", n)
    r = Roll.load(card)
    assert len(r.shots(card)) == 4                        # old photo excluded
    cli.main(["develop", "--card", str(card), "--size", "screen"])
    out = list((card / "KFILM" / "PRINTS").rglob("*.jpg"))
    assert len(out) == 5                                  # 4 prints + contact sheet
    assert Roll.load(card) is None                        # archived after developing


def test_realistic_needs_rewind(card):
    cli.main(["load", "grit400", "--card", str(card), "--mode", "realistic", "--frames", "12"])
    _shot(card / "DCIM" / "100CANON", 2)
    with pytest.raises(SystemExit):
        cli.main(["develop", "--card", str(card)])
    cli.main(["open-back", "--card", str(card)])
    assert Roll.load(card).fog_frames == [1]
    cli.main(["rewind", "--card", str(card)])
    cli.main(["develop", "--card", str(card), "--size", "screen"])


def test_frames_past_end_are_skipped(card):
    cli.main(["load", "sun200", "--card", str(card), "--frames", "12"])
    for n in range(2, 16):
        _shot(card / "DCIM" / "100CANON", n)
    exposed, extra = Roll.load(card).frames_on_roll(card)
    assert len(exposed) == 12 and len(extra) == 2


def test_raw_plus_jpeg_counts_once(card):
    cli.main(["load", "studio160", "--card", str(card)])
    _shot(card / "DCIM" / "100CANON", 2)
    shutil.copy(card / "DCIM" / "100CANON" / "IMG_0002.JPG",
                card / "DCIM" / "100CANON" / "IMG_0002.CR2")
    shots = Roll.load(card).shots(card)
    assert len(shots) == 1 and shots[0].suffix == ".CR2"


def test_recipe_stocks_exist_and_are_warm_or_neutral():
    rgb = np.full((8, 8, 3), 0.18, np.float32)
    for sid in ["summerchrome", "leicax", "fuji200", "reggieportra", "nostalgicneg"]:
        s = dataclasses.replace(STOCKS[sid], grain=0)
        y = develop(rgb, s)
        assert y[..., 0].mean() >= y[..., 2].mean() - 0.02, sid   # no strong blue cast on grey
