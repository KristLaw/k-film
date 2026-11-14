"""Find the camera's SD card, so `--card` can be left out."""
from __future__ import annotations

import os
import string
import sys
from pathlib import Path


def candidates() -> list[Path]:
    if sys.platform == "darwin":
        roots = [p for p in Path("/Volumes").iterdir() if p.is_dir()] if Path("/Volumes").is_dir() else []
    elif os.name == "nt":
        roots = [Path(f"{d}:\\") for d in string.ascii_uppercase if Path(f"{d}:\\").exists()]
    else:
        user = os.environ.get("USER", "")
        roots = [p for base in (Path("/media") / user, Path("/run/media") / user, Path("/mnt"))
                 if base.is_dir() for p in base.iterdir()]
    return [r for r in roots if (r / "DCIM").is_dir()]


def find_card(given: str | None) -> Path:
    if given:
        return Path(given)
    found = candidates()
    if len(found) == 1:
        return found[0]
    if not found:
        raise SystemExit("No camera card found (a drive with a DCIM folder). "
                         "Put the card in, or pass --card /Volumes/EOS_DIGITAL")
    raise SystemExit("More than one card found: " + ", ".join(map(str, found)) +
                     ". Pick one with --card.")
