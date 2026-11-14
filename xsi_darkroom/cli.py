"""Command line: `xsi <command>`."""
from __future__ import annotations

import argparse
import dataclasses
import sys
from pathlib import Path

from . import __version__
from .contact import contact_sheet, light_leak
from .hald import HaldCLUT, identity_hald
from .process import SIZES, print_frame
from .roll import Roll, new_roll
from .stocks import STOCKS, get


def _pushed(stock, push: float):
    """Push processing adds contrast and grain; pulling softens."""
    if not push:
        return stock
    return dataclasses.replace(
        stock,
        contrast=stock.contrast * (1 + 0.08 * push),
        grain=stock.grain * (1 + 0.3 * push) if push > 0 else stock.grain * (1 + 0.1 * push),
        fade=max(0.0, stock.fade - 0.01 * push),
    )


def cmd_stocks(a):
    kinds = {"color": "Colour negative", "slide": "Slide", "bw": "Black & white"}
    for k, title in kinds.items():
        print(f"\n{title}")
        for s in STOCKS.values():
            if s.kind == k:
                print(f"  {s.id:<10} {s.name:<14} ISO {s.iso:<5} {s.notes}  (inspired by {s.inspired_by})")
    print("\nSet the 450D to the ISO shown, shoot RAW, and keep Review time Off.")


def cmd_load(a):
    card = Path(a.card)
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
    stock = get(a.stock)
    frames = a.frames or stock.frames
    r = new_roll(card, stock.id, frames, a.mode, a.push)
    push = f", pushed {a.push:+g}" if a.push else ""
    print(f"Loaded {stock.name} (ISO {stock.iso}{push}), {frames} exposures, {r.mode} mode.")
    print(f"Set your 450D to ISO {_iso(stock.iso, a.push)} and RAW. Happy shooting.")


def _iso(iso, push):
    return int(round(iso * 2 ** push))


def cmd_status(a):
    card = Path(a.card)
    r = Roll.load(card)
    if not r:
        print("No roll loaded. `xsi load <stock> --card <card>`")
        return
    s = get(r.stock)
    exposed, extra = r.frames_on_roll(card)
    left = r.frames - len(exposed)
    print(f"{s.name} · {len(exposed)}/{r.frames} exposed · {left} left · mode {r.mode}"
          + (" · rewound" if r.rewound else ""))
    if extra:
        print(f"  {len(extra)} shot(s) after the end of the roll won't be developed.")
    if left == 0 and r.mode == "realistic" and not r.rewound:
        print("  End of roll. Rewind before opening the back: `xsi rewind`.")


def cmd_rewind(a):
    card = Path(a.card)
    r = Roll.load(card)
    if not r:
        sys.exit("No roll loaded.")
    r.rewound = True
    r.save(card)
    print(f"Rewound {get(r.stock).name}. Ready for the darkroom: `xsi develop`.")


def cmd_open_back(a):
    card = Path(a.card)
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
    card = Path(a.card)
    r = Roll.load(card)
    if not r:
        sys.exit("No roll loaded.")
    ok, why = r.ready_to_develop(card)
    if not ok:
        sys.exit(why)
    stock = _pushed(get(a.stock or r.stock), r.push)
    lut = HaldCLUT(a.lut) if a.lut else None
    exposed, extra = r.frames_on_roll(card)
    out = Path(a.out or card / "XSIROLL" / "PRINTS" / f"{stock.id}_{int(r.loaded_at)}")
    prints = []
    for i, p in enumerate(exposed, 1):
        dst = out / f"{i:02d}_{p.stem}.jpg"
        print(f"  developing frame {i:>2}/{len(exposed)}  {p.name}", flush=True)
        print_frame(p, stock, dst, size=a.size, ev=a.ev, seed=i, lut=lut)
        if i in r.fog_frames:
            from PIL import Image
            light_leak(Image.open(dst), seed=i).save(dst, quality=92)
        prints.append(dst)
    sheet = contact_sheet(prints, stock, out / "contact_sheet.jpg")
    print(f"Done: {len(prints)} prints in {out}\nContact sheet: {sheet}")
    if extra:
        print(f"({len(extra)} shot(s) past the end of the roll were skipped.)")
    r.developed = True
    r.archive(card)


def cmd_print(a):
    stock = get(a.stock)
    lut = HaldCLUT(a.lut) if a.lut else None
    for f in a.files:
        p = Path(f)
        dst = Path(a.out) / f"{p.stem}_{stock.id}.jpg"
        print_frame(p, stock, dst, size=a.size, ev=a.ev, lut=lut)
        print(dst)


def cmd_hald(a):
    identity_hald(a.level).save(a.out)
    print(f"Neutral HaldCLUT written to {a.out}. Grade it in any editor, then use --lut.")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="xsi", description="Film-camera workflow for the Canon EOS 450D / Rebel XSi")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("stocks", help="list film stocks").set_defaults(fn=cmd_stocks)

    p = sub.add_parser("load", help="load a roll onto the SD card")
    p.add_argument("stock")
    p.add_argument("--card", required=True, help="SD card root (folder containing DCIM)")
    p.add_argument("--frames", type=int, choices=[12, 24, 27, 36], help="exposures (default 36)")
    p.add_argument("--mode", choices=["basic", "realistic"], default="basic")
    p.add_argument("--push", type=float, default=0.0, help="push/pull in stops, e.g. 1 or -1")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_load)

    for name, fn, h in (("status", cmd_status, "frames left on the roll"),
                        ("rewind", cmd_rewind, "rewind the roll (realistic mode)")):
        p = sub.add_parser(name, help=h)
        p.add_argument("--card", required=True)
        p.set_defaults(fn=fn)

    p = sub.add_parser("open-back", help="oops: open the camera back mid-roll (light leaks)")
    p.add_argument("--card", required=True)
    p.set_defaults(fn=cmd_open_back)

    p = sub.add_parser("develop", help="develop the roll into prints + contact sheet")
    p.add_argument("--card", required=True)
    p.add_argument("--out")
    p.add_argument("--size", choices=list(SIZES), default="web")
    p.add_argument("--ev", type=float, default=0.0, help="print exposure correction")
    p.add_argument("--stock", help="override the stock (cross-processing!)")
    p.add_argument("--lut", help="optional HaldCLUT PNG applied after the film curve")
    p.set_defaults(fn=cmd_develop)

    p = sub.add_parser("print", help="develop single files without a roll")
    p.add_argument("stock")
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

    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
