"""Make a K-Film roll readable by M-Film's desktop app, Darkrooms.

M-Film's camera writes a roll log next to the photos, and Darkrooms reads
it to find the rolls on a card (format from M-Film's filmroll.c, v0.2.1):

    DCIM/100CANON/ROLL_024.TXT

    # ML film mode roll log (filmroll module)
    roll = 024
    film = portra400
    exposures = 24
    loaded = 2026-10-25 14:03:11

    1  IMG_0012.CR2  2026-10-25 14:05:40  f/2.8
    2  IMG_0013.CR2  2026-10-25 14:06:02  f/5.6

    # rewound 2026-10-25 18:00:00 after 2 of 24 frames

K-Film writes the same file from its own roll, so a 450D card shows up in
Darkrooms. Darkrooms only knows M-Film's film keys, so a K-Film film is
logged as its nearest M-Film film (films.DARKROOMS_NEAREST).
"""
from __future__ import annotations

import re
import struct
import time
from pathlib import Path

HEADER = "# ML film mode roll log (filmroll module)"


# ---------------------------------------------------------------- EXIF
def _tiff_tags(data: bytes, base: int = 0):
    """Yield (tag, type, count, value_bytes_or_offset, endian) from a TIFF."""
    end = "<" if data[base:base + 2] == b"II" else ">"
    (ifd,) = struct.unpack(end + "I", data[base + 4:base + 8])
    return end, ifd


def _read_ifd(data: bytes, base: int, off: int, end: str) -> dict:
    out = {}
    if off <= 0 or base + off + 2 > len(data):
        return out
    (n,) = struct.unpack(end + "H", data[base + off:base + off + 2])
    for i in range(n):
        e = base + off + 2 + 12 * i
        if e + 12 > len(data):
            break
        tag, typ, cnt = struct.unpack(end + "HHI", data[e:e + 8])
        raw = data[e + 8:e + 12]
        size = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1, 10: 8}.get(typ, 1) * cnt
        if size > 4:
            (p,) = struct.unpack(end + "I", raw)
            raw = data[base + p:base + p + size]
        out[tag] = (typ, cnt, raw)
    return out


def read_exif(path: Path) -> tuple[str | None, str | None]:
    """(DateTimeOriginal 'YYYY-MM-DD HH:MM:SS', f-number '2.8') from a CR2 or
    JPEG; None where it can't be read."""
    try:
        data = Path(path).read_bytes()[:262144]
    except OSError:
        return None, None
    base = 0
    if data[:2] == b"\xff\xd8":                       # JPEG: find APP1 Exif
        i = data.find(b"Exif\x00\x00")
        if i < 0:
            return None, None
        base = i + 6
    if data[base:base + 2] not in (b"II", b"MM"):
        return None, None
    end, ifd0 = _tiff_tags(data, base)
    t0 = _read_ifd(data, base, ifd0, end)
    exif = {}
    if 0x8769 in t0:
        (p,) = struct.unpack(end + "I", t0[0x8769][2][:4])
        exif = _read_ifd(data, base, p, end)
    when = None
    for tags, tag in ((exif, 0x9003), (t0, 0x0132)):
        if tag in tags:
            s = tags[tag][2].split(b"\x00")[0].decode("ascii", "replace")
            m = re.match(r"(\d{4}):(\d\d):(\d\d) (\d\d:\d\d:\d\d)", s)
            if m:
                when = f"{m[1]}-{m[2]}-{m[3]} {m[4]}"
                break
    fnum = None
    if 0x829D in exif:
        num, den = struct.unpack(end + "II", exif[0x829D][2][:8])
        if den:
            fnum = f"{num / den:.1f}".rstrip("0").rstrip(".")
    return when, fnum


# ---------------------------------------------------------------- the log
def _stamp(t: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))


def next_roll_number(card: Path) -> int:
    used = [int(m[1]) for p in Path(card).glob("DCIM/*/ROLL_*.TXT")
            if (m := re.match(r"ROLL_(\d{3})\.TXT$", p.name, re.I))]
    return (max(used) % 999 + 1) if used else 1


def log_path(card: Path, number: int, first_frame: Path | None = None) -> Path:
    folder = first_frame.parent if first_frame else None
    if folder is None:
        folders = sorted(Path(card).glob("DCIM/[0-9][0-9][0-9]*"))
        folder = folders[0] if folders else Path(card) / "DCIM" / "100CANON"
    return folder / f"ROLL_{number:03d}.TXT"


def render_log(number: int, film_key: str, exposures: int, loaded_at: float,
               frames: list[Path], rewound_at: float | None = None) -> str:
    lines = [HEADER, f"roll = {number:03d}", f"film = {film_key}",
             f"exposures = {exposures}", f"loaded = {_stamp(loaded_at)}", ""]
    for i, p in enumerate(frames, 1):
        when, fnum = read_exif(p)
        when = when or _stamp(p.stat().st_mtime)
        lines.append(f"{i}  {p.name}  {when}" + (f"  f/{fnum}" if fnum else ""))
    text = "\n".join(lines) + "\n"
    if rewound_at is not None:
        text += f"\n# rewound {_stamp(rewound_at)} after {len(frames)} of {exposures} frames\n"
    return text


def write_log(card: Path, roll, film_key: str) -> Path:
    """Write (or refresh) the Darkrooms roll log for a K-Film roll."""
    frames, _ = roll.frames_on_roll(card)
    if not roll.log_number:
        roll.log_number = next_roll_number(card)
    p = log_path(card, roll.log_number, frames[0] if frames else None)
    # if the first frame moved folders, don't leave an old copy behind
    for old in Path(card).glob(f"DCIM/*/ROLL_{roll.log_number:03d}.TXT"):
        if old != p:
            old.unlink()
    p.parent.mkdir(parents=True, exist_ok=True)
    rewound = roll.rewound_at if roll.rewound else None
    p.write_text(render_log(roll.log_number, film_key, roll.frames, roll.loaded_at,
                            frames, rewound), newline="\n")
    return p
