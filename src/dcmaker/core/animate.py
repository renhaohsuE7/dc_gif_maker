"""Animated pipeline: any ffmpeg-readable animation source (GIF file or a
captured PNG frame sequence) -> budget-fitted GIF or APNG on an exact square
transparent canvas.

For each candidate artwork size the budget search finds the highest fps that
fits, then one result is picked per priority (frames/balanced/resolution)."""
from __future__ import annotations

import os
import shutil
import tempfile
from typing import Callable, Protocol

from ..adapters.ffmpeg import FFmpeg, InputSpec
from ..adapters.gifsicle import Gifsicle
from ..adapters.tools import ToolError
from ..presets import Preset
from .budget import FitResult, byte_ceiling, choose, fit_fps
from .geometry import content_sizes, geom_square

ProgressCb = Callable[[str], None]


class Encoder(Protocol):
    ext: str
    def encode(self, chain: str, out: str) -> int: ...
    def measure(self, path: str) -> tuple[int, int, int]: ...


class GifEncoder:
    """ffmpeg palettegen/paletteuse + gifsicle lossy (1-bit transparency)."""
    ext = "gif"

    def __init__(self, ff: FFmpeg, gifsicle: Gifsicle, src: InputSpec,
                 tmp: str, colors: int = 256, dither: str = "none",
                 lossy: int = 60):
        self.ff, self.gifsicle, self.src, self.tmp = ff, gifsicle, src, tmp
        self.colors, self.dither, self.lossy = colors, dither, lossy

    def encode(self, chain: str, out: str) -> int:
        raw = os.path.join(self.tmp, "raw.gif")
        pal = os.path.join(self.tmp, "pal.png")
        self.ff.gif_two_pass(self.src, chain, pal, raw, self.colors, self.dither)
        self.gifsicle.optimize(raw, out, self.lossy)
        return os.path.getsize(out)

    def measure(self, path: str) -> tuple[int, int, int]:
        w, h = self.ff.dimensions(path)
        return w, h, self.ff.count_frames(path)


class ApngEncoder:
    """ffmpeg APNG: full 8-bit alpha (soft edges), usually bigger than GIF so
    the search settles on a lower fps for the same budget."""
    ext = "png"

    def __init__(self, ff: FFmpeg, src: InputSpec, tmp: str):
        self.ff, self.src, self.tmp = ff, src, tmp

    def encode(self, chain: str, out: str) -> int:
        self.ff.apng(self.src, chain, out)
        return os.path.getsize(out)

    def measure(self, path: str) -> tuple[int, int, int]:
        w, h = self.ff.dimensions(path)
        return w, h, self.ff.count_frames(path)


class WebpEncoder:
    """ffmpeg libwebp animated WebP: true colour + full 8-bit alpha (no GIF
    palette or dithering), yet a fraction of an APNG's size — so it fills the
    same budget with APNG-grade quality instead of GIF-grade palettes.
    `quality` is libwebp's 0-100 lossy scale (lowered to fit if needed).

    ffprobe's webp demuxer can't report the size/frame count of an animated
    WebP ("image data not found"), so `measure()` parses the RIFF container
    directly instead."""
    ext = "webp"

    def __init__(self, ff: FFmpeg, src: InputSpec, tmp: str, quality: int = 80):
        self.ff, self.src, self.tmp, self.quality = ff, src, tmp, quality

    def encode(self, chain: str, out: str) -> int:
        self.ff.webp(self.src, chain, out, self.quality)
        return os.path.getsize(out)

    def measure(self, path: str) -> tuple[int, int, int]:
        return webp_info(path)


def webp_info(path: str) -> tuple[int, int, int]:
    """(canvas_width, canvas_height, frame_count) read straight from the WebP
    RIFF container. VP8X holds the canvas size; each animation frame is an
    ANMF chunk. Self-contained (no ffprobe, which mis-probes animated WebP)."""
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ToolError(f"not a WebP file: {path}")
    w = h = frames = 0
    pos = 12
    while pos + 8 <= len(data):
        fourcc = data[pos:pos + 4]
        size = int.from_bytes(data[pos + 4:pos + 8], "little")
        body = pos + 8
        if fourcc == b"VP8X" and body + 10 <= len(data):
            w = int.from_bytes(data[body + 4:body + 7], "little") + 1
            h = int.from_bytes(data[body + 7:body + 10], "little") + 1
        elif fourcc == b"ANMF":
            frames += 1
        pos = body + size + (size & 1)   # chunks are padded to even length
    return w, h, frames


def compress_animated(enc: Encoder, src: InputSpec, trim: str,
                      preset: Preset, priority: str, min_fps: float,
                      out: str, tmp: str,
                      progress: ProgressCb = lambda s: None) -> FitResult:
    """Run the candidate x fps budget search and write the picked file to
    `out`. `tmp` is a caller-owned scratch dir (the encoder shares it)."""
    target = byte_ceiling(preset.target_kb)
    results: list[FitResult] = []

    for content in content_sizes(preset.canvas, preset.content_fracs):
        label = f"{content}in{preset.canvas}"
        geom = geom_square(preset.canvas, content)
        trial = os.path.join(tmp, f"trial_{label}.{enc.ext}")

        def encode_at(fps: float, _geom=geom, _trial=trial) -> int:
            return enc.encode(f"{trim}fps={fps:.4f},{_geom}", _trial)

        best = fit_fps(encode_at, src.fps, min_fps, target)
        if best is None:
            progress(f"  {label:>9}  (cannot fit even at {min_fps:g}fps)")
            continue
        final = os.path.join(tmp, f"best_{label}.{enc.ext}")
        enc.encode(f"{trim}fps={best[0]:.4f},{geom}", final)
        w, h, frames = enc.measure(final)
        r = FitResult(label, w, h, round(best[0], 2), frames,
                      os.path.getsize(final), final, content)
        progress(f"  {label:>9}  out={w}x{h} art={content:<4} fps={r.fps:<6g} "
                 f"frames={r.frames:<4} {r.size / 1024:.0f}KB")
        results.append(r)

    if not results:
        raise ValueError(
            f"nothing fits {preset.target_kb}KB: raise the budget, lower "
            f"min-fps, or trim/shorten the clip")

    pick = choose(results, priority)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    shutil.copyfile(pick.path, out)
    pick.path = out
    return pick


def make_scratch() -> tempfile.TemporaryDirectory:
    return tempfile.TemporaryDirectory(prefix="dcmaker-")
