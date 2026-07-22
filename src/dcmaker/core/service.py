"""convert(): the single business-logic entry point shared by CLI and web.

Routes by input kind x requested format:
    svg-static / raster  -> exact-square transparent PNG
    gif                  -> budget-fitted GIF or APNG
    svg-animated         -> Chromium frame capture -> budget-fitted GIF/APNG
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable

from ..adapters.browser import capture_svg_frames
from ..adapters.ffmpeg import FFmpeg
from ..adapters.gifsicle import Gifsicle
from ..adapters.pngtools import PngQuant
from ..adapters.svgrender import SvgRenderer
from ..config import Settings, load_settings
from ..presets import PRESETS, PRIORITIES, Preset
from .animate import (ApngEncoder, Encoder, GifEncoder, WebpEncoder,
                      compress_animated, make_scratch)
from .budget import FitResult
from .detect import detect_kind
from .geometry import build_trim, parse_time

FORMATS = ("auto", "gif", "apng", "png", "webp")
ANIMATED_KINDS = {"gif", "svg-animated"}
# output file extension per resolved format (apng is a .png container)
_EXT = {"gif": "gif", "apng": "png", "png": "png", "webp": "webp"}


@dataclass
class ConvertRequest:
    input_path: str
    preset: str = "sticker"
    fmt: str = "auto"
    priority: str | None = None      # default: preset's
    ss: str | None = None            # trim start (seconds or [HH:]MM:SS)
    to: str | None = None            # trim end
    duration: float | None = None    # animated SVG: capture length (auto)
    lossy: int | None = None         # GIF route only; default: preset's
    quality: int | None = None       # WebP route only; default: preset's
    colors: int = 256
    dither: str = "none"
    min_fps: float | None = None
    out: str | None = None
    out_dir: str | None = None


@dataclass
class ConvertResult:
    path: str
    fmt: str
    kind: str
    preset: str
    size: int
    width: int
    height: int
    frames: int
    fps: float
    artwork_px: int
    notes: list[str] = field(default_factory=list)


def resolve_format(kind: str, fmt: str) -> str:
    if fmt not in FORMATS:
        raise ValueError(f"format must be one of {FORMATS}")
    if kind in ANIMATED_KINDS:
        if fmt == "png":
            raise ValueError("input is animated; pick gif, apng or webp "
                             "(or trim it yourself)")
        return "gif" if fmt == "auto" else fmt
    if fmt in ("gif", "apng", "webp"):
        raise ValueError("input is static; there is nothing to animate — "
                         "output format is png")
    return "png"


def derive_out(input_path: str, suffix: str, ext: str,
               out: str | None = None, out_dir: str | None = None) -> str:
    """Explicit --out wins; else <stem>-<suffix>.<ext> inside --out-dir, or
    (when input sits in an 'original/' folder) a sibling 'output/', otherwise
    next to the input."""
    if out:
        return out
    stem = os.path.splitext(os.path.basename(input_path))[0]
    fname = f"{stem}-{suffix}.{ext}"
    if out_dir:
        return os.path.join(out_dir, fname)
    in_parent = os.path.dirname(os.path.abspath(input_path))
    base = (os.path.join(os.path.dirname(in_parent), "output")
            if os.path.basename(in_parent) == "original" else in_parent)
    return os.path.join(base, fname)


def convert(req: ConvertRequest, settings: Settings | None = None,
            progress: Callable[[str], None] = lambda s: None) -> ConvertResult:
    settings = settings or load_settings()
    if not os.path.isfile(req.input_path):
        raise ValueError(f"input not found: {req.input_path}")
    preset = PRESETS.get(req.preset)
    if preset is None:
        raise ValueError(f"preset must be one of {tuple(PRESETS)}")
    if req.priority is not None and req.priority not in PRIORITIES:
        raise ValueError(f"priority must be one of {PRIORITIES}")

    kind = detect_kind(req.input_path)
    fmt = resolve_format(kind, req.fmt)
    ext = _EXT[fmt]
    out = derive_out(req.input_path, f"dc_{preset.name}_{fmt}", ext,
                     req.out, req.out_dir)

    ff = FFmpeg(settings.ffmpeg, settings.ffprobe)
    progress(f"[route] {kind} -> {fmt}  preset={preset.name} "
             f"({preset.canvas}x{preset.canvas}, <={preset.target_kb}KB)")

    if fmt == "png":
        return _static(req, settings, preset, ff, kind, out)
    return _animated(req, settings, preset, ff, kind, fmt, out, progress)


def _static(req: ConvertRequest, settings: Settings, preset: Preset,
            ff: FFmpeg, kind: str, out: str) -> ConvertResult:
    from .static import compress_static
    renderer = SvgRenderer(settings.rsvg_convert) if kind == "svg-static" else None
    with make_scratch() as tmp:
        r = compress_static(ff, renderer, PngQuant(settings.pngquant),
                            req.input_path, kind == "svg-static", preset,
                            out, tmp)
    return _result(r, "png", kind, preset)


def _animated(req: ConvertRequest, settings: Settings, preset: Preset,
              ff: FFmpeg, kind: str, fmt: str, out: str,
              progress: Callable[[str], None]) -> ConvertResult:
    ss = parse_time(req.ss) if req.ss is not None else None
    to = parse_time(req.to) if req.to is not None else None
    if ss is not None and ss < 0:
        raise ValueError("--ss must be >= 0")
    if ss is not None and to is not None and to <= ss:
        raise ValueError(f"--to ({to:g}s) must be greater than --ss ({ss:g}s)")
    trim = build_trim(ss, to)

    min_fps = req.min_fps if req.min_fps is not None else preset.min_fps
    priority = req.priority or preset.priority
    lossy = req.lossy if req.lossy is not None else preset.lossy
    quality = req.quality if req.quality is not None else preset.webp_quality
    notes: list[str] = []

    with make_scratch() as tmp:
        if kind == "svg-animated":
            # capture once at 2x canvas; the fps filter downsamples per trial
            cap = capture_svg_frames(
                req.input_path, os.path.join(tmp, "frames"),
                box=preset.canvas * 2, fps=settings.capture_fps,
                duration=req.duration,
                default_duration=settings.default_duration,
                max_seconds=settings.capture_max_seconds)
            src = ff.frames_input(cap.frames_dir, cap.fps)
            notes.append(f"captured {cap.frames} frames @ {cap.fps:g}fps "
                         f"({cap.duration:g}s) at {preset.canvas * 2}px")
            progress(f"[capture] {notes[-1]}")
        else:
            src = ff.file_input(req.input_path)

        progress(f"[source] {src.width}x{src.height}  {src.frames} frames  "
                 f"{src.fps:g}fps")
        # borderline clips can miss the budget at the preset's default
        # quality knob; escalate toward more compression (visible artifacts
        # beat "does not fit") unless the user pinned the knob themselves.
        # GIF's lossy climbs; WebP's quality drops; APNG has no such knob.
        if fmt == "gif":
            knob = "lossy"
            steps: list[int | None] = (
                [lossy] if req.lossy is not None
                else [lossy, lossy + 40, lossy + 80])
        elif fmt == "webp":
            knob = "quality"
            steps = ([quality] if req.quality is not None
                     else list(dict.fromkeys(
                         [quality, max(quality - 20, 20),
                          max(quality - 40, 10)])))
        else:  # apng: no quality knob to escalate
            knob = ""
            steps = [None]

        def make_encoder(step: int | None) -> Encoder:
            if fmt == "gif":
                return GifEncoder(ff, Gifsicle(settings.gifsicle), src, tmp,
                                  req.colors, req.dither, step)
            if fmt == "webp":
                return WebpEncoder(ff, src, tmp, step)
            return ApngEncoder(ff, src, tmp)

        for i, step in enumerate(steps):
            try:
                r = compress_animated(make_encoder(step), src, trim,
                                      preset, priority, min_fps, out, tmp,
                                      progress)
                if i:
                    verb = "raised" if fmt == "gif" else "lowered"
                    notes.append(f"{knob} {verb} to {step} to fit budget")
                break
            except ValueError:
                if i == len(steps) - 1:
                    raise
                progress(f"[retry] nothing fits at {knob}={step}, "
                         f"trying {knob}={steps[i + 1]}")
    res = _result(r, fmt, kind, preset)
    res.notes = notes
    return res


def _result(r: FitResult, fmt: str, kind: str, preset: Preset) -> ConvertResult:
    return ConvertResult(path=r.path, fmt=fmt, kind=kind, preset=preset.name,
                         size=r.size, width=r.width, height=r.height,
                         frames=r.frames, fps=r.fps, artwork_px=r.key)
