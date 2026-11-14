"""Write JPEGs a Canon EOS camera can show in Playback.

Canon's playback wants a DCF file: a baseline JPEG that starts with an Exif
APP1 (no JFIF), carries a 160 x 120 thumbnail in IFD1, and sits in a DCF
folder (DCIM/100CANON) with an 8-character DCF name (KFLM0001.JPG).
The page is 2256 x 1504, the 450D's own Small size.
"""
from __future__ import annotations

import io
import struct
import time
from pathlib import Path

from PIL import Image

ASCII, SHORT, LONG, RATIONAL, UNDEFINED = 2, 3, 4, 5, 7
_SIZE = {ASCII: 1, SHORT: 2, LONG: 4, RATIONAL: 8, UNDEFINED: 1}


def _ifd(entries: list, base: int, next_ifd: int = 0) -> tuple[bytes, list]:
    """One IFD at offset `base`; returns (bytes, positions of LONG
    placeholders to patch). entries: (tag, type, value)."""
    entries = sorted(entries)
    head = struct.pack("<H", len(entries))
    data = b""
    data_at = base + 2 + 12 * len(entries) + 4
    body = b""
    for tag, typ, val in entries:
        if typ == ASCII:
            raw = val.encode("ascii") + b"\0"
            count = len(raw)
        elif typ == UNDEFINED:
            raw, count = val, len(val)
        elif typ == SHORT:
            raw, count = struct.pack("<H", val), 1
        elif typ == LONG:
            raw, count = struct.pack("<I", val), 1
        else:  # RATIONAL
            raw, count = struct.pack("<II", *val), 1
        if len(raw) <= 4:
            body += struct.pack("<HHI", tag, typ, count) + raw.ljust(4, b"\0")
        else:
            body += struct.pack("<HHII", tag, typ, count, data_at + len(data))
            data += raw + (b"\0" if len(raw) % 2 else b"")
    return head + body + struct.pack("<I", next_ifd) + data


def exif_app1(width: int, height: int, thumb: bytes, when: float | None = None) -> bytes:
    stamp = time.strftime("%Y:%m:%d %H:%M:%S", time.localtime(when or time.time()))
    res = (72, 1)

    def ifd0(exif_at, ifd1_at):
        return [(0x010F, ASCII, "Canon"), (0x0110, ASCII, "Canon EOS 450D"),
                (0x0112, SHORT, 1), (0x011A, RATIONAL, res), (0x011B, RATIONAL, res),
                (0x0128, SHORT, 2), (0x0131, ASCII, "Karafilm"), (0x0132, ASCII, stamp),
                (0x0213, SHORT, 2), (0x8769, LONG, exif_at)], ifd1_at

    exif = [(0x9000, UNDEFINED, b"0221"), (0x9003, ASCII, stamp), (0x9004, ASCII, stamp),
            (0x9101, UNDEFINED, b"\x01\x02\x03\x00"), (0xA000, UNDEFINED, b"0100"),
            (0xA001, SHORT, 1), (0xA002, LONG, width), (0xA003, LONG, height)]

    def ifd1(thumb_at):
        return [(0x0103, SHORT, 6), (0x011A, RATIONAL, res), (0x011B, RATIONAL, res),
                (0x0128, SHORT, 2), (0x0201, LONG, thumb_at), (0x0202, LONG, len(thumb))]

    # lay out twice: sizes first, then the real offsets
    e0, _ = ifd0(0, 0)
    b0 = _ifd(e0, 8)
    be = _ifd(exif, 8 + len(b0))
    b1 = _ifd(ifd1(0), 8 + len(b0) + len(be))
    exif_at, ifd1_at = 8 + len(b0), 8 + len(b0) + len(be)
    thumb_at = ifd1_at + len(b1)
    e0, nxt = ifd0(exif_at, ifd1_at)
    tiff = (b"II*\0" + struct.pack("<I", 8) + _ifd(e0, 8, nxt) + _ifd(exif, exif_at)
            + _ifd(ifd1(thumb_at), ifd1_at) + thumb)
    payload = b"Exif\0\0" + tiff
    assert len(payload) + 2 < 65536
    return b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload


def _jpeg(im: Image.Image, quality: int) -> bytes:
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=quality, subsampling=1, optimize=False, progressive=False)
    data = buf.getvalue()
    # drop Pillow's JFIF APP0: Canon files start with Exif
    if data[2:4] == b"\xff\xe0":
        (n,) = struct.unpack(">H", data[4:6])
        data = data[:2] + data[4 + n:]
    return data


def thumbnail(im: Image.Image) -> bytes:
    """160 x 120 with black bars, as Canon makes them for 3:2 frames."""
    t = Image.new("RGB", (160, 120), (0, 0, 0))
    small = im.convert("RGB").resize((160, 107), Image.LANCZOS)
    t.paste(small, (0, 6))
    return _jpeg(t, 85)


def save_dcf(im: Image.Image, path: Path, quality: int = 92, when: float | None = None) -> Path:
    im = im.convert("RGB")
    main = _jpeg(im, quality)
    app1 = exif_app1(im.width, im.height, thumbnail(im), when)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(main[:2] + app1 + main[2:])
    return path
