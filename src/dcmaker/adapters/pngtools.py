"""Optional PNG size reduction via pngquant (palette quantisation). Used only
when a static PNG exceeds its budget — rare for 320px art."""
from __future__ import annotations

import os

from .tools import find_tool, run


class PngQuant:
    def __init__(self, pngquant: str = ""):
        self.bin = find_tool("pngquant", pngquant)

    @property
    def available(self) -> bool:
        return bool(self.bin)

    def compress(self, src: str, out: str) -> bool:
        """Quantise to an optimised palette. Returns False when unavailable or
        when pngquant refuses (quality floor). Keeps full alpha."""
        if not self.bin:
            return False
        proc = run([self.bin, "--force", "--skip-if-larger", "--strip",
                    "--quality", "60-95", "--output", out, src])
        return proc.returncode == 0 and os.path.isfile(out)
