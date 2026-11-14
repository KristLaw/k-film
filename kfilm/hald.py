"""Optional HaldCLUT support.

Bring your own film LUTs (for example the free RawTherapee "Film Simulation"
HaldCLUT collection). No LUTs are bundled with this project.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


class HaldCLUT:
    def __init__(self, path: str | Path):
        im = Image.open(path).convert("RGB")
        w, h = im.size
        if w != h:
            raise ValueError("HaldCLUT image must be square")
        level = round((w) ** (1 / 3))
        if level ** 3 != w:
            raise ValueError(f"{path}: size {w} is not a HaldCLUT (level^3)")
        n = level * level                       # entries per axis
        arr = np.asarray(im, dtype=np.float32).reshape(-1, 3) / 255.0
        # Hald order: red fastest, then green, then blue.
        self.table = arr.reshape(n, n, n, 3)    # [b, g, r]
        self.n = n
        self.name = Path(path).stem

    def apply(self, y: np.ndarray) -> np.ndarray:
        n = self.n
        x = np.clip(y, 0, 1) * (n - 1)
        i0 = np.floor(x).astype(np.int32)
        i1 = np.minimum(i0 + 1, n - 1)
        f = x - i0
        r0, g0, b0 = i0[..., 0], i0[..., 1], i0[..., 2]
        r1, g1, b1 = i1[..., 0], i1[..., 1], i1[..., 2]
        fr, fg, fb = f[..., 0:1], f[..., 1:2], f[..., 2:3]
        t = self.table

        def lerp(a, b, w):
            return a + (b - a) * w

        c00 = lerp(t[b0, g0, r0], t[b0, g0, r1], fr)
        c01 = lerp(t[b0, g1, r0], t[b0, g1, r1], fr)
        c10 = lerp(t[b1, g0, r0], t[b1, g0, r1], fr)
        c11 = lerp(t[b1, g1, r0], t[b1, g1, r1], fr)
        c0 = lerp(c00, c01, fg)
        c1 = lerp(c10, c11, fg)
        return lerp(c0, c1, fb).astype(np.float32)


def identity_hald(level: int = 8) -> Image.Image:
    """Generate a neutral HaldCLUT (handy for making your own in an editor)."""
    n = level * level
    v = np.linspace(0, 255, n).round().astype(np.uint8)
    b, g, r = np.meshgrid(v, v, v, indexing="ij")
    arr = np.stack([r, g, b], -1).reshape(level ** 3, level ** 3, 3)
    return Image.fromarray(arr, "RGB")
