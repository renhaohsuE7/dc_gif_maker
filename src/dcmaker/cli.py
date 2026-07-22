"""Thin CLI: parse args, delegate to core.service.convert, print the result.

Examples:
    dcmaker samples/original/x.gif                          # sticker GIF
    dcmaker samples/original/x.gif --preset emoji           # emoji GIF
    dcmaker samples/original/x.gif --format apng            # sticker APNG
    dcmaker samples/original/x.gif --format webp            # animated WebP
    dcmaker samples/original/logo.svg                       # static -> PNG
    dcmaker samples/original/anim.svg --duration 4          # animated SVG
    dcmaker samples/original/x.gif --ss 0 --to 5 --priority resolution
"""
from __future__ import annotations

import argparse
import sys

from .core.service import (FORMATS, ConvertRequest, ConvertResult, convert,
                           convert_all, convert_many, is_batch_input,
                           iter_inputs)
from .presets import PRESETS, PRIORITIES, STRATEGIES


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dcmaker",
        description="Discord emoji + sticker maker: GIF/SVG/PNG in, "
                    "budget-fitted GIF/APNG/PNG out (transparency kept).")
    p.add_argument("input", help="source file (.gif .svg .png .jpg .webp), "
                                 "or a directory / glob for a batch run")
    p.add_argument("--recursive", action="store_true",
                   help="batch: also scan subdirectories of a directory input")
    p.add_argument("--on-error", choices=("stop", "skip"), default="skip",
                   help="batch: skip = record a failing file and continue "
                        "(default) | stop = abort on the first failure")
    p.add_argument("--preset", choices=[*PRESETS, "all"], default="sticker",
                   help="output route: " + " | ".join(
                       f"{k} = {v.desc}" for k, v in PRESETS.items())
                   + " | all = both from one run (一句指令、雙產出)")
    p.add_argument("--strategy", choices=list(STRATEGIES), default=None,
                   help="GIF slimming lever: " + " | ".join(
                       f"{k} = {v.desc}" for k, v in STRATEGIES.items()))
    p.add_argument("--format", dest="fmt", choices=list(FORMATS),
                   default="auto",
                   help="auto = gif for animated inputs, png for static; "
                        "gif | apng | webp for animation; png for static")
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
    p.add_argument("--quality", type=int, default=None,
                   help="WebP libwebp quality 0-100, higher = better/bigger "
                        "(default: preset's)")
    p.add_argument("--colors", type=int, default=None,
                   help="pin the GIF palette size (strategy ladders won't "
                        "move a pinned value)")
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
        duration=args.duration, lossy=args.lossy, quality=args.quality,
        strategy=args.strategy, colors=args.colors, dither=args.dither,
        min_fps=args.min_fps, out=args.out, out_dir=args.out_dir)
    if is_batch_input(args.input):
        _run_batch(args, req)
        return
    try:
        rs = (convert_all(req, progress=print) if args.preset == "all"
              else [convert(req, progress=print)])
    except ValueError as exc:
        sys.exit(f"[error] {exc}")
    for r in rs:
        _print_one(r)


def _print_one(r: ConvertResult) -> None:
    print(f"\n[picked] {r.preset}/{r.fmt}: {r.width}x{r.height} "
          f"artwork={r.artwork_px}px  {r.frames} frames  {r.fps:g}fps  "
          f"colors={r.colors}  {r.size / 1024:.0f}KB")
    print(f"[written] {r.path}  ({r.size} bytes)")


def _run_batch(args, req: ConvertRequest) -> None:
    supported, unsupported = iter_inputs(args.input, args.recursive)
    if not supported and not unsupported:
        sys.exit(f"[error] no files found under {args.input!r}")
    try:
        results = convert_many(supported, req, on_error=args.on_error,
                               progress=print)
    except ValueError as exc:
        sys.exit(f"[error] {exc}")
    ok = [b for b in results if b.results]
    failed = [b for b in results if b.error]
    print(f"\n[summary] {len(ok)} converted / {len(unsupported)} skipped / "
          f"{len(failed)} failed")
    for b in ok:
        for r in b.results:
            print(f"  [ok]   {b.path} -> {r.path} ({r.size / 1024:.0f}KB)")
    for path in unsupported:
        print(f"  [skip] {path} — unsupported type")
    for b in failed:
        print(f"  [fail] {b.path} — {b.error}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
