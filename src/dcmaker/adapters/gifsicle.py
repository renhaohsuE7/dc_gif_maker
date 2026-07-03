"""gifsicle adapter: the lossy-LZW optimisation pass (~40-50% extra saving)."""
from __future__ import annotations

from .tools import require_tool, run


class Gifsicle:
    def __init__(self, gifsicle: str = ""):
        self.bin = require_tool("gifsicle", gifsicle)

    def optimize(self, src: str, out: str, lossy: int) -> None:
        run([self.bin, "-O3", f"--lossy={lossy}", src, "-o", out], check=True)
