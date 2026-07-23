"""Fixed output routes for Discord. Specs verified 2026-07-02, see
docs/references/external_sites/2026-07-02-discord-sticker-emoji-specs.md:
stickers must be exactly 320x320 and <=512KB (PNG/APNG recommended, GIF ok);
emoji <256KB, 128x128 recommended (shown at 32px), GIF/PNG/WebP ok."""
from __future__ import annotations

from dataclasses import dataclass, field

PRIORITIES = ("frames", "balanced", "resolution")


@dataclass(frozen=True)
class Preset:
    name: str
    desc: str
    target_kb: int
    canvas: int                 # exact square output edge in px
    lossy: int                  # gifsicle lossy strength (GIF route only)
    webp_quality: int           # libwebp quality 0-100 (WebP route only)
    min_fps: float
    priority: str               # default selection among fitting candidates
    # candidate artwork sizes as a fraction of the canvas; smaller artwork
    # leaves a transparent margin but buys many more frames under budget
    content_fracs: tuple[float, ...] = (1.0,)
    # `balanced` strategy palette — the eye-ranked winner per preset, see
    # docs/experiments/2026-07-23-strategy-matrix.md
    balanced_colors: int = 256


STICKER = Preset(
    name="sticker",
    desc="Discord sticker (exactly 320x320, <=512KB)",
    target_kb=512, canvas=320, lossy=100, webp_quality=80, min_fps=2.0,
    priority="frames",
    content_fracs=(0.44, 0.53, 0.63, 0.75, 0.88, 1.0),
    balanced_colors=96,   # viewed large: banding shows, keep colour fidelity
)

EMOJI = Preset(
    name="emoji",
    desc="Discord emoji (128x128, <256KB, shown at 32px)",
    target_kb=256, canvas=128, lossy=60, webp_quality=72, min_fps=4.0,
    priority="frames",
    content_fracs=(1.0,),
    balanced_colors=32,   # shown at 32px: colours invisible, buy frames
)

PRESETS: dict[str, Preset] = {p.name: p for p in (STICKER, EMOJI)}


# ----------------------------------------------------------------- strategies
@dataclass(frozen=True)
class Strategy:
    """How the GIF route reaches the byte budget — which lever gives first.
    `rungs` are the palette sizes tried in order; `pin_fps` holds the source
    fps while walking the rungs, so frames only drop once the ladder is
    exhausted."""
    name: str
    desc: str
    rungs: tuple[int, ...]
    pin_fps: bool


FRAMES = Strategy(
    name="frames",
    desc="keep 256 colours, fit by lowering fps",
    rungs=(256,), pin_fps=False)

COLORS = Strategy(
    name="colors",
    desc="keep the source fps, fit by shrinking the palette",
    rungs=(256, 192, 128, 96, 64, 48, 32), pin_fps=True)

BALANCED = Strategy(
    name="balanced",
    desc="eye-validated frames+colours blend: per-preset palette (sticker 96, "
         "emoji 32) + fps search — see "
         "docs/experiments/2026-07-23-strategy-matrix.md",
    rungs=(), pin_fps=False)   # empty = resolved from Preset.balanced_colors

STRATEGIES: dict[str, Strategy] = {s.name: s
                                   for s in (BALANCED, FRAMES, COLORS)}
DEFAULT_STRATEGY = "balanced"   # validated 2026-07-23 (strategy-matrix)
