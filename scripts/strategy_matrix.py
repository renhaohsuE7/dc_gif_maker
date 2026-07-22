"""Strategy-matrix experiment (openspec change add-dual-output-strategies).

Renders the fps x colours grid — every cell budget-fitted by the existing fps
search at a pinned palette — into an HTML contact sheet for human ranking.
The user's eye picks the winning combination; that ranking (recorded under
docs/experiments/) then defines the `balanced` strategy.

Run inside the dcmaker image (repo mounted read-only, output dir writable):

    docker run --rm --memory=2g \
      -v "$PWD":/work:ro -v "$PWD/samples/output":/outdir \
      -w /work -e PYTHONPATH=/work/src \
      --entrypoint python dcmaker:latest \
      scripts/strategy_matrix.py --out-dir /outdir/strategy_matrix
"""
from __future__ import annotations

import argparse
import html
import os
import sys

from dcmaker.core.service import ConvertRequest, convert

FIXTURES = ("samples/original/hajime_todoroki_02.gif",
            "samples/original/star_spin.svg")
PRESETS = ("sticker", "emoji")
COLOURS = (256, 128, 96, 64, 32)

CSS = """
body { font: 14px/1.5 system-ui, 'Noto Sans TC', sans-serif; margin: 2rem;
       background: #1e1f22; color: #dbdee1; }
h1 { font-size: 1.3rem; } h2 { font-size: 1.05rem; margin: 2rem 0 .5rem; }
p.hint { color: #949ba4; max-width: 60rem; }
.row { display: flex; gap: 1rem; flex-wrap: wrap; align-items: flex-end; }
figure { margin: 0; text-align: center; }
figure img { background:
  repeating-conic-gradient(#2b2d31 0% 25%, #313338 0% 50%) 0 0/16px 16px;
  border-radius: 8px; }
figcaption { color: #949ba4; font-size: .8rem; margin-top: .3rem;
  font-variant-numeric: tabular-nums; }
figcaption b { color: #dbdee1; }
"""


def cell(fixture: str, preset: str, colours: int, out_dir: str) -> dict:
    stem = os.path.splitext(os.path.basename(fixture))[0]
    name = f"{stem}-{preset}-c{colours}.gif"
    out = os.path.join(out_dir, "cells", name)
    r = convert(ConvertRequest(fixture, preset=preset, fmt="gif",
                               colors=colours, out=out),
                progress=lambda s: None)
    print(f"  {stem} {preset:7} c={colours:<3} -> {r.frames} frames "
          f"{r.fps:g}fps {r.size // 1024}KB", flush=True)
    return {"name": name, "colours": colours, "fps": r.fps,
            "frames": r.frames, "kb": r.size // 1024, "w": r.width}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", default="samples/output/strategy_matrix")
    ap.add_argument("--colours", type=int, nargs="+", default=list(COLOURS))
    args = ap.parse_args(argv)
    os.makedirs(os.path.join(args.out_dir, "cells"), exist_ok=True)

    sections = []
    for fixture in FIXTURES:
        if not os.path.isfile(fixture):
            print(f"skip missing fixture {fixture}", file=sys.stderr)
            continue
        for preset in PRESETS:
            print(f"[{fixture} × {preset}]", flush=True)
            cells = [cell(fixture, preset, c, args.out_dir)
                     for c in args.colours]
            sections.append((os.path.basename(fixture), preset, cells))

    figs = lambda cs: "\n".join(  # noqa: E731
        f'<figure><img src="cells/{html.escape(c["name"])}" '
        f'width="{min(c["w"], 320)}" loading="lazy">'
        f'<figcaption><b>{c["colours"]} 色</b><br>'
        f'{c["fps"]:g} fps · {c["frames"]} 幀 · {c["kb"]} KB</figcaption>'
        f"</figure>" for c in cs)
    body = "\n".join(
        f"<h2>{html.escape(fx)} — {pr}</h2>\n<div class='row'>{figs(cs)}</div>"
        for fx, pr, cs in sections)
    doc = ("<!doctype html><meta charset='utf-8'>"
           "<title>dcmaker 策略矩陣 — 肉眼排名</title>"
           f"<style>{CSS}</style>"
           "<h1>策略矩陣:同一預算下「色彩 vs 幀數」的取捨</h1>"
           "<p class='hint'>每一格都塞進同一個 Discord 預算 —— 色數越少,"
           "自動搜尋能塞進的幀數越多(越順),但色帶/色偏越明顯。"
           "請憑肉眼挑出每一列「效果最好」的色數,回報給 Claude:"
           "它會成為 balanced 策略的定義。</p>"
           f"{body}")
    path = os.path.join(args.out_dir, "index.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(doc)
    print(f"\ncontact sheet -> {path}")


if __name__ == "__main__":
    main()
