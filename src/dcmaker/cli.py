"""Thin CLI: parse args, delegate to core.service.convert, print the result.

Examples:
    dcmaker samples/original/x.gif                          # sticker GIF
    dcmaker samples/original/x.gif --preset emoji           # emoji GIF
    dcmaker samples/original/x.gif --format apng            # sticker APNG
    dcmaker samples/original/logo.svg                       # static -> PNG
    dcmaker samples/original/anim.svg --duration 4          # animated SVG
    dcmaker samples/original/x.gif --ss 0 --to 5 --priority resolution
"""
from __future__ import annotations

import argparse
import sys

from .core.service import FORMATS, ConvertRequest, convert
from .presets import PRESETS, PRIORITIES


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dcmaker",
        description="Discord emoji + sticker maker: GIF/SVG/PNG in, "
                    "budget-fitted GIF/APNG/PNG out (transparency kept).")
    p.add_argument("input", help="source file (.gif .svg .png .jpg .webp)")
    p.add_argument("--preset", choices=list(PRESETS), default="sticker",
                   help="output route: " + " | ".join(
                       f"{k} = {v.desc}" for k, v in PRESETS.items()))
    p.add_argument("--format", dest="fmt", choices=list(FORMATS),
                   default="auto",
                   help="auto = gif for animated inputs, png for static")
    p.add_argument("--priority", choices=list(PRIORITIES), default=None,
                   help="frames (smoothest) | resolution (biggest artwork) | "
                        "balanced (default: preset's)")
    p.add_argument("--ss", help="trim: start time (seconds or [HH:]MM:SS)")
    p.add_argument("--to", help="trim: end time — shortening the clip is the "
                                "biggest size lever")
    p.add_argument("--duration", type=float, default=None,
                   help="animated SVG: seconds to capture (default: detected "
                        "from the animation, else DCM_DEFAULT_DURATION)")
    p.add_argument("--lossy", type=int, default=None,
                   help="GIF gifsicle lossy strength (default: preset's)")
    p.add_argument("--colors", type=int, default=256)
    p.add_argument("--dither", default="none")
    p.add_argument("--min-fps", type=float, default=None)
    p.add_argument("--out", help="explicit output file path")
    p.add_argument("--out-dir", help="output directory (filename derived)")
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    req = ConvertRequest(
        input_path=args.input, preset=args.preset, fmt=args.fmt,
        priority=args.priority, ss=args.ss, to=args.to,
        duration=args.duration, lossy=args.lossy, colors=args.colors,
        dither=args.dither, min_fps=args.min_fps,
        out=args.out, out_dir=args.out_dir)
    try:
        r = convert(req, progress=print)
    except ValueError as exc:
        sys.exit(f"[error] {exc}")
    print(f"\n[picked] {r.preset}/{r.fmt}: {r.width}x{r.height} "
          f"artwork={r.artwork_px}px  {r.frames} frames  {r.fps:g}fps  "
          f"{r.size / 1024:.0f}KB")
    print(f"[written] {r.path}  ({r.size} bytes)")


if __name__ == "__main__":
    main()
