"""Static pipeline: SVG or raster image -> exact-square transparent PNG.

SVG's transparent-by-default vector nature is the whole point here: rasterise
at the artwork box, pad to the exact canvas, and the result is almost always
far below the Discord budget. pngquant is only a fallback for pathological
inputs (e.g. photos)."""
from __future__ import annotations

import os
import shutil

from ..adapters.ffmpeg import FFmpeg
from ..adapters.pngtools import PngQuant
from ..adapters.svgrender import SvgRenderer
from ..presets import Preset
from .budget import FitResult, byte_ceiling
from .geometry import geom_square


def compress_static(ff: FFmpeg, svg: SvgRenderer | None, quant: PngQuant,
                    input_path: str, is_svg: bool, preset: Preset,
                    out: str, tmp: str) -> FitResult:
    target = byte_ceiling(preset.target_kb)
    canvas = preset.canvas

    src_png = input_path
    if is_svg:
        if svg is None:
            raise ValueError("no SVG renderer available")
        src_png = os.path.join(tmp, "rendered.png")
        svg.render_png(input_path, src_png, canvas)

    padded = os.path.join(tmp, "padded.png")
    ff.still_png(src_png, geom_square(canvas), padded)

    if os.path.getsize(padded) > target:
        quantised = os.path.join(tmp, "quantised.png")
        if quant.compress(padded, quantised) and \
                os.path.getsize(quantised) <= target:
            padded = quantised
        else:
            raise ValueError(
                f"static PNG exceeds {preset.target_kb}KB even after "
                f"quantisation — simplify the artwork")

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    shutil.copyfile(padded, out)
    w, h = ff.dimensions(out)
    return FitResult("static", w, h, 0.0, 1, os.path.getsize(out), out, canvas)
