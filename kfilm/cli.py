"""Command line: `kfilm <command>` (`xsi` still works)."""
from __future__ import annotations

import argparse
import dataclasses
import io
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

from . import __version__, darkrooms
from .card import find_card
from .contact import contact_sheet, light_leak
from .films import Film, all_films, get
from .hald import HaldCLUT, identity_hald
from .process import SIZES, print_frame
from .roll import Roll, new_roll, roll_dir


# ---------------------------------------------------------------- helpers
def _pushed(film: Film, push: float) -> Film:
    """Push processing adds contrast and grain; pulling softens."""
    if not push:
        return film
    if film.engine == "kfilm":
        s = film.stock
        s = dataclasses.replace(
            s, contrast=s.contrast * (1 + 0.08 * push),
            grain=s.grain * (1 + 0.3 * push) if push > 0 else s.grain * (1 + 0.1 * push),
            fade=max(0.0, s.fade - 0.01 * push))
        return dataclasses.replace(film, stock=s)
    d = dict(film.data)
    d["contrast"] = tuple(c * (1 + 0.08 * push) for c in d["contrast"])
    d["grain"] = d.get("grain", 0) * (1 + (0.3 if push > 0 else 0.1) * push)
    return dataclasses.replace(film, data=d)


def _iso(iso, push):
    """ISO to set on the 450D: it goes 100..1600 (3200 as H)."""
    return int(round(iso * 2 ** push))


def _iso_text(iso, push=0.0) -> str:
    want = _iso(iso, push)
    if want < 100:
        return f"ISO 100 (the 450D's lowest; dial exposure comp. +{__import__('math').log2(100 / want):.1g} for box speed {want})"
    if want > 1600:
        return f"ISO {min(want, 3200)} ('H' in C.Fn ISO expansion)" if want <= 3200 else "ISO 3200 ('H'), and push in the darkroom"
    return f"ISO {want}"


def _sync(card: Path, r: Roll, quiet: bool = False) -> None:
    """Refresh the Darkrooms roll log next to the photos."""
    if not r.darkrooms:
        return
    p = darkrooms.write_log(card, r, r.darkrooms)
    r.save(card)
    if not quiet:
        print(f"Darkrooms roll log: {p.relative_to(card)} (film = {r.darkrooms})")


# ---------------------------------------------------------------- commands
def cmd_films(a):
    films = all_films().values()
    shelves: dict[str, list[Film]] = {}
    for f in films:
        shelves.setdefault(f.shelf, []).append(f)
    for shelf, items in shelves.items():
        if a.shelf and a.shelf.lower() not in shelf.lower():
            continue
        print(f"\n{shelf} ({len(items)})")
        for f in sorted(items, key=lambda f: (f.iso, f.id)):
            print(f"  {f.id:<16} {f.name:<28} ISO {f.iso:<5} {f.notes}")
    print(f"\n{len(all_films())} films. Set the 450D to the ISO shown, shoot RAW, Review time Off.")
    print("M-Film films marked LUT look best after `kfilm getluts` (once).")


def cmd_load(a):
    card = find_card(a.card)
    old = Roll.load(card)
    if old and not old.developed and old.shots(card):
        if old.mode == "realistic" and not old.rewound and not a.force:
            sys.exit("A roll is still in the camera and not rewound. Rewind it, develop it, "
                     "or use --force to open the back (fogs the roll).")
        if not a.force:
            sys.exit(f"Roll of {old.stock} still loaded with {len(old.shots(card))} frames. "
                     "Develop it first or use --force.")
        if old.mode == "realistic" and not old.rewound:
            print("You opened the back on an unrewound roll. It's ruined (archived, not developed).")
        old.archive(card)
    film = get(a.film)
    frames = a.frames or film.frames
    dr = "" if a.no_darkrooms else (a.darkrooms_film or film.darkrooms_key or "")
    r = new_roll(card, film.id, frames, a.mode, a.push, darkrooms=dr)
    push = f", pushed {a.push:+g}" if a.push else ""
    print(f"Loaded {film.name} (ISO {film.iso}{push}), {frames} exposures, {r.mode} mode.")
    print(f"Set your 450D to {_iso_text(film.iso, a.push)}, Quality RAW, Review time Off. Happy shooting.")
    _camera_lines(film)
    _sync(card, r)


def _camera_lines(film: Film) -> None:
    from .camera450d import settings
    s = settings(film)
    print("Optional, for the camera's own preview JPEGs (the RAW stays the same):")
    for line in s.lines():
        print(f"  {line}")


def cmd_camera(a):
    film = get(a.film)
    print(f"{film.name} on the 450D: {_iso_text(film.iso)}, Quality RAW, Review time Off")
    _camera_lines(film)


def cmd_status(a):
    card = find_card(a.card)
    r = Roll.load(card)
    if not r:
        print("No roll loaded. `kfilm load <film>`")
        return
    f = get(r.stock)
    exposed, extra = r.frames_on_roll(card)
    left = r.frames - len(exposed)
    print(f"{f.name} · {len(exposed)}/{r.frames} exposed · {left} left · mode {r.mode}"
          + (" · rewound" if r.rewound else ""))
    if extra:
        print(f"  {len(extra)} shot(s) after the end of the roll won't be developed.")
    if left == 0 and r.mode == "realistic" and not r.rewound:
        print("  End of roll. Rewind before opening the back: `kfilm rewind`.")
    _sync(card, r)


def cmd_sync(a):
    card = find_card(a.card)
    r = Roll.load(card)
    if not r:
        sys.exit("No roll loaded.")
    if a.film:
        get(a.film)                      # must be a real film
        r.darkrooms = a.film
    if not r.darkrooms:
        r.darkrooms = get(r.stock).darkrooms_key or ""
    if not r.darkrooms:
        sys.exit("This film has no M-Film match. Pick one: `kfilm sync --film portra400`.")
    _sync(card, r)
    print("Open Darkrooms with the card in: the roll is on the shelf.")


def cmd_rewind(a):
    card = find_card(a.card)
    r = Roll.load(card)
    if not r:
        sys.exit("No roll loaded.")
    r.rewound, r.rewound_at = True, time.time()
    r.save(card)
    print(f"Rewound {get(r.stock).name}. Ready for the darkroom: `kfilm develop`.")
    _sync(card, r)


def cmd_open_back(a):
    card = find_card(a.card)
    r = Roll.load(card)
    if not r:
        sys.exit("No roll loaded.")
    n = len(r.frames_on_roll(card)[0])
    if r.rewound:
        print("Roll is rewound, so opening the back is safe.")
        return
    hit = [i for i in range(max(1, n - 2), n + 1) if i not in r.fog_frames]
    r.fog_frames += hit
    r.save(card)
    print(f"Light hit the film! Frames {hit} will show light leaks." if hit else "Nothing exposed yet.")


def cmd_develop(a):
    card = find_card(a.card)
    r = Roll.load(card)
    if not r:
        sys.exit("No roll loaded.")
    ok, why = r.ready_to_develop(card)
    if not ok:
        sys.exit(why)
    _sync(card, r, quiet=True)
    film = _pushed(get(a.film or r.stock), r.push)
    lut = HaldCLUT(a.lut) if a.lut else None
    exposed, extra = r.frames_on_roll(card)
    out = Path(a.out or roll_dir(card) / "PRINTS" / f"{film.id}_{int(r.loaded_at)}")
    prints = []
    for i, p in enumerate(exposed, 1):
        dst = out / f"{i:02d}_{p.stem}.jpg"
        print(f"  developing frame {i:>2}/{len(exposed)}  {p.name}", flush=True)
        print_frame(p, film, dst, size=a.size, ev=a.ev, seed=i, lut=lut)
        if i in r.fog_frames:
            from PIL import Image
            light_leak(Image.open(dst), seed=i).save(dst, quality=92)
        prints.append(dst)
    sheet = contact_sheet(prints, film, out / "contact_sheet.jpg")
    print(f"Done: {len(prints)} prints in {out}\nContact sheet: {sheet}")
    if extra:
        print(f"({len(extra)} shot(s) past the end of the roll were skipped.)")
    r.developed = True
    r.archive(card)


def cmd_print(a):
    film = get(a.film)
    lut = HaldCLUT(a.lut) if a.lut else None
    for f in a.files:
        p = Path(f)
        dst = Path(a.out) / f"{p.stem}_{film.id}.jpg"
        print_frame(p, film, dst, size=a.size, ev=a.ev, lut=lut)
        print(dst)


def cmd_hald(a):
    identity_hald(a.level).save(a.out)
    print(f"Neutral HaldCLUT written to {a.out}. Grade it in any editor, then use --lut.")


def cmd_getluts(a):
    """Fetch the Film-Luts LUTs (MIT, by Yahia Angelo) the M-Film films use."""
    from .mfilm import lut_dir
    from .mfilm_filmluts import STOCKS, ZIP, REPO
    want = {f"{path}.cube" for _, path, *_ in STOCKS}
    dest = lut_dir() / "filmluts"
    got = {}
    if a.source:
        root = Path(a.source).expanduser()
        for rel in want:
            for cand in (root / rel, root / "luts" / rel):
                if cand.is_file():
                    got[rel] = cand.read_bytes()
                    break
    elif a.zip:
        data = Path(a.zip).expanduser().read_bytes()
    else:
        print(f"Downloading the Film-Luts collection (~40 MB) from {REPO} ...", flush=True)
        if shutil.which("curl"):
            data = subprocess.run(["curl", "-fsSL", ZIP], capture_output=True, check=True).stdout
        else:
            with urllib.request.urlopen(ZIP) as resp:
                data = resp.read()
    if not a.source:
        z = zipfile.ZipFile(io.BytesIO(data))
        for name in z.namelist():
            rel = name.split("/", 1)[1] if "/" in name else name
            if rel.startswith("luts/"):            # the collection keeps them under luts/
                rel = rel[5:]
            if rel in want:
                got[rel] = z.read(name)
            elif rel.upper() == "LICENSE":
                (dest).mkdir(parents=True, exist_ok=True)
                (dest / "LICENSE-Film-Luts.txt").write_bytes(z.read(name))
    for rel, b in got.items():
        p = dest / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b)
    print(f"{len(got)} of {len(want)} LUTs in {dest}")


# ---------------------------------------------------------------- parser
def main(argv=None):
    ap = argparse.ArgumentParser(prog="kfilm", description="Shoot a Canon EOS 450D like a film camera")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name in ("films", "stocks"):
        p = sub.add_parser(name, help="list every film" if name == "films" else argparse.SUPPRESS)
        p.add_argument("--shelf", help="only one shelf, e.g. recipes, k-film, m-film bw")
        p.set_defaults(fn=cmd_films)

    def card_arg(p):
        p.add_argument("--card", help="SD card root (found by itself when one card is in)")

    p = sub.add_parser("load", help="load a roll onto the SD card")
    p.add_argument("film")
    card_arg(p)
    p.add_argument("--frames", type=int, choices=[12, 24, 27, 36], help="exposures (default 36)")
    p.add_argument("--mode", choices=["basic", "realistic"], default="basic")
    p.add_argument("--push", type=float, default=0.0, help="push/pull in stops, e.g. 1 or -1")
    p.add_argument("--force", action="store_true")
    p.add_argument("--no-darkrooms", action="store_true", help="don't write the Darkrooms roll log")
    p.add_argument("--darkrooms-film", help="M-Film film key to show in Darkrooms")
    p.set_defaults(fn=cmd_load)

    for name, fn, h in (("status", cmd_status, "frames left on the roll"),
                        ("rewind", cmd_rewind, "rewind the roll (realistic mode)"),
                        ("open-back", cmd_open_back, "oops: open the camera back mid-roll (light leaks)")):
        p = sub.add_parser(name, help=h)
        card_arg(p)
        p.set_defaults(fn=fn)

    p = sub.add_parser("camera", help="what to set on the 450D for a film")
    p.add_argument("film")
    p.set_defaults(fn=cmd_camera)

    p = sub.add_parser("sync", help="write the roll log M-Film's Darkrooms app reads")
    card_arg(p)
    p.add_argument("--film", help="M-Film film key Darkrooms should use")
    p.set_defaults(fn=cmd_sync)

    p = sub.add_parser("develop", help="develop the roll into prints + contact sheet")
    card_arg(p)
    p.add_argument("--out")
    p.add_argument("--size", choices=list(SIZES), default="web")
    p.add_argument("--ev", type=float, default=0.0, help="print exposure correction")
    p.add_argument("--film", "--stock", dest="film", help="develop as another film (cross-processing!)")
    p.add_argument("--lut", help="optional HaldCLUT PNG applied after the film")
    p.set_defaults(fn=cmd_develop)

    p = sub.add_parser("print", help="develop single files without a roll")
    p.add_argument("film")
    p.add_argument("files", nargs="+")
    p.add_argument("--out", default="prints")
    p.add_argument("--size", choices=list(SIZES), default="web")
    p.add_argument("--ev", type=float, default=0.0)
    p.add_argument("--lut")
    p.set_defaults(fn=cmd_print)

    p = sub.add_parser("hald", help="write a neutral HaldCLUT to make your own look")
    p.add_argument("--level", type=int, default=8)
    p.add_argument("--out", default="identity_hald.png")
    p.set_defaults(fn=cmd_hald)

    p = sub.add_parser("getluts", help="download the Film-Luts colours for the M-Film films (once)")
    p.add_argument("--from", dest="source", help="a Film-Luts clone you already have")
    p.add_argument("--zip", help="a Film-Luts zip you already downloaded")
    p.set_defaults(fn=cmd_getluts)

    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
