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
    min_fps: float
    priority: str               # default selection among fitting candidates
    # candidate artwork sizes as a fraction of the canvas; smaller artwork
    # leaves a transparent margin but buys many more frames under budget
    content_fracs: tuple[float, ...] = (1.0,)


STICKER = Preset(
    name="sticker",
    desc="Discord sticker (exactly 320x320, <=512KB)",
    target_kb=512, canvas=320, lossy=100, min_fps=2.0, priority="frames",
    content_fracs=(0.44, 0.53, 0.63, 0.75, 0.88, 1.0),
)

EMOJI = Preset(
    name="emoji",
    desc="Discord emoji (128x128, <256KB, shown at 32px)",
    target_kb=256, canvas=128, lossy=60, min_fps=4.0, priority="frames",
    content_fracs=(1.0,),
)

PRESETS: dict[str, Preset] = {p.name: p for p in (STICKER, EMOJI)}
