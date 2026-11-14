"""Roll bookkeeping on the SD card.

The 450D can't run custom code, so the "roll" lives as a small JSON file on
the card (KFILM/ROLL.JSON; cards from XSi Darkroom 0.1 used XSIROLL/). When you load a roll we remember every photo already on the card;
everything you shoot after that belongs to the roll, in shooting order.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROLL_DIR = "KFILM"
LEGACY_DIR = "XSIROLL"
PHOTO_EXT = {".cr2", ".jpg", ".jpeg"}


def roll_dir(card: Path) -> Path:
    """KFILM/, or XSIROLL/ on a card that still has an XSi Darkroom 0.1 roll."""
    new, old = Path(card) / ROLL_DIR, Path(card) / LEGACY_DIR
    return old if old.is_dir() and not new.is_dir() else new


@dataclass
class Roll:
    stock: str
    frames: int
    mode: str = "basic"            # basic | realistic
    push: float = 0.0              # stops of push (+) or pull (-) processing
    loaded_at: float = field(default_factory=time.time)
    existing: list = field(default_factory=list)
    rewound: bool = False
    fog_frames: list = field(default_factory=list)  # frames hit by light
    developed: bool = False
    rewound_at: float | None = None
    darkrooms: str = ""            # M-Film film key in the Darkrooms roll log ("" = off)
    log_number: int = 0            # ROLL_nnn.TXT

    # ------------------------------------------------------------ storage
    @staticmethod
    def path(card: Path) -> Path:
        return roll_dir(card) / "ROLL.JSON"

    def save(self, card: Path) -> None:
        p = self.path(card)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(asdict(self), indent=1))

    @classmethod
    def load(cls, card: Path) -> "Roll | None":
        p = cls.path(card)
        if not p.exists():
            return None
        d = json.loads(p.read_text())
        known = cls.__dataclass_fields__
        return cls(**{k: v for k, v in d.items() if k in known})

    def archive(self, card: Path) -> None:
        hist = roll_dir(card) / "HISTORY.JSON"
        items = json.loads(hist.read_text()) if hist.exists() else []
        d = asdict(self)
        d.pop("existing")
        items.append(d)
        hist.write_text(json.dumps(items, indent=1))
        self.path(card).unlink(missing_ok=True)

    # ------------------------------------------------------------ frames
    def shots(self, card: Path) -> list[Path]:
        """Photos taken since the roll was loaded, oldest first.

        RAW+JPEG pairs count as one frame (the CR2 wins)."""
        seen = set(self.existing)
        new = [p for p in scan_card(card) if _key(card, p) not in seen]
        by_stem: dict[str, Path] = {}
        for p in new:
            k = str(p.with_suffix("")).lower()
            if k not in by_stem or p.suffix.lower() == ".cr2":
                by_stem[k] = p
        return sorted(by_stem.values(), key=_order)

    def frames_on_roll(self, card: Path) -> tuple[list[Path], list[Path]]:
        """(exposed frames, shots taken after the roll ran out)."""
        s = self.shots(card)
        return s[: self.frames], s[self.frames:]

    def is_finished(self, card: Path) -> bool:
        return len(self.shots(card)) >= self.frames

    def ready_to_develop(self, card: Path) -> tuple[bool, str]:
        exposed, _ = self.frames_on_roll(card)
        if not exposed:
            return False, "No frames shot on this roll yet."
        if self.mode == "realistic" and not self.rewound:
            return False, ("Realistic mode: rewind the roll first (`kfilm rewind`). "
                           "Opening the back now would fog it.")
        return True, ""


def scan_card(card: Path) -> list[Path]:
    dcim = Path(card) / "DCIM"
    root = dcim if dcim.exists() else Path(card)
    return [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in PHOTO_EXT
            and ROLL_DIR not in p.parts and LEGACY_DIR not in p.parts
            and not p.name.upper().startswith("KFLM")]     # Karafilm shelf pages


def _key(card: Path, p: Path) -> str:
    return str(Path(p).relative_to(card)).replace("\\", "/").lower()


def _order(p: Path):
    """Canon order: folder number (100CANON, 101CANON...) then file number."""
    folder = re.match(r"(\d+)", p.parent.name)
    num = re.search(r"(\d{4})", p.stem)
    return (int(folder.group(1)) if folder else 0,
            int(num.group(1)) if num else 0, p.stat().st_mtime)


def new_roll(card: Path, stock: str, frames: int, mode: str, push: float,
             darkrooms: str = "") -> Roll:
    existing = [_key(card, p) for p in scan_card(card)]
    r = Roll(stock=stock, frames=frames, mode=mode, push=push, existing=existing,
             darkrooms=darkrooms)
    r.save(card)
    return r
