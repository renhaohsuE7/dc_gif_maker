"""ffmpeg / ffprobe adapter. All ffmpeg invocations in the project funnel
through this module; business logic never builds ffmpeg commands itself."""
from __future__ import annotations

import os
from dataclasses import dataclass

from .tools import ToolError, require_tool, run


@dataclass(frozen=True)
class InputSpec:
    """An animation source ffmpeg can read: either a single animated file
    (GIF/APNG/WebP) or a numbered PNG frame sequence captured from a browser."""
    args: tuple[str, ...]   # ffmpeg input arguments, e.g. ("-i", "x.gif")
    fps: float
    width: int
    height: int
    frames: int


class FFmpeg:
    def __init__(self, ffmpeg: str = "", ffprobe: str = ""):
        self.ffmpeg = require_tool("ffmpeg", ffmpeg)
        self.ffprobe = require_tool("ffprobe", ffprobe)

    # ---------------------------------------------------------------- probe
    def _probe(self, path: str, entries: str) -> str:
        return run([self.ffprobe, "-v", "error", "-select_streams", "v:0",
                    "-show_entries", entries,
                    "-of", "default=noprint_wrappers=1:nokey=1", path],
                   check=True).stdout.strip()

    def file_input(self, path: str) -> InputSpec:
        w = int(self._probe(path, "stream=width"))
        h = int(self._probe(path, "stream=height"))
        num, _, den = self._probe(path, "stream=r_frame_rate").partition("/")
        fps = float(num) / float(den or 1)
        fr = self._probe(path, "stream=nb_frames")
        return InputSpec(("-i", path), fps, w, h, int(fr) if fr.isdigit() else 0)

    def frames_input(self, frames_dir: str, fps: float,
                     pattern: str = "frame_%05d.png") -> InputSpec:
        files = sorted(f for f in os.listdir(frames_dir)
                       if f.startswith("frame_") and f.endswith(".png"))
        if not files:
            raise ToolError(f"no captured frames in {frames_dir}")
        first = os.path.join(frames_dir, files[0])
        w = int(self._probe(first, "stream=width"))
        h = int(self._probe(first, "stream=height"))
        return InputSpec(("-framerate", f"{fps:g}",
                          "-i", os.path.join(frames_dir, pattern)),
                         fps, w, h, len(files))

    def count_frames(self, path: str) -> int:
        out = run([self.ffprobe, "-v", "error", "-select_streams", "v:0",
                   "-count_frames", "-show_entries", "stream=nb_read_frames",
                   "-of", "default=noprint_wrappers=1:nokey=1", path]).stdout.strip()
        return int(out) if out.isdigit() else 0

    def dimensions(self, path: str) -> tuple[int, int]:
        return (int(self._probe(path, "stream=width")),
                int(self._probe(path, "stream=height")))

    # --------------------------------------------------------------- encode
    def gif_two_pass(self, src: InputSpec, chain: str, palette_png: str,
                     out: str, colors: int, dither: str) -> None:
        """palettegen -> paletteuse with transparency reserved. `chain` is the
        shared trim/fps/geometry filter prefix so both passes see identical
        frames."""
        gen = (f"{chain},palettegen=stats_mode=diff:max_colors={colors}"
               f":reserve_transparent=1")
        run([self.ffmpeg, "-y", "-v", "error", *src.args, "-vf", gen,
             palette_png], check=True)
        use = (f"{chain}[x];[x][1:v]paletteuse=dither={dither}"
               f":diff_mode=rectangle:alpha_threshold=128")
        run([self.ffmpeg, "-y", "-v", "error", *src.args, "-i", palette_png,
             "-lavfi", use, out], check=True)

    def apng(self, src: InputSpec, chain: str, out: str) -> None:
        """Full 8-bit-alpha APNG, infinite loop. `-pred mixed` is the best
        zlib predictor for flat-colour art."""
        run([self.ffmpeg, "-y", "-v", "error", *src.args,
             "-vf", f"{chain},format=rgba",
             "-f", "apng", "-plays", "0", "-pred", "mixed", out], check=True)

    def still_png(self, src_png: str, chain: str, out: str) -> None:
        """Apply a scale/pad chain to a single image (static route)."""
        run([self.ffmpeg, "-y", "-v", "error", "-i", src_png,
             "-vf", chain, "-frames:v", "1", out], check=True)
