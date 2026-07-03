"""ffmpeg filter fragments describing resize/pad geometry, plus trim/time
helpers. Pure string builders — no subprocess calls."""
from __future__ import annotations


def geom_square(canvas: int, content: int | None = None) -> str:
    """Fit artwork inside a content x content box keeping aspect, then pad to
    an exact canvas x canvas square with a fully transparent background.
    Smaller content => more transparent margin => fewer pixels => higher fps
    for the same budget (the artwork just appears smaller)."""
    content = content or canvas
    return (f"format=rgba,"
            f"scale={content}:{content}:force_original_aspect_ratio=decrease"
            f":flags=lanczos,"
            f"pad={canvas}:{canvas}:(ow-iw)/2:(oh-ih)/2:color=black@0.0")


def parse_time(s: str | float) -> float:
    """Timestamp to seconds: float seconds ('2.5') or '[HH:]MM:SS(.ms)'."""
    s = str(s).strip()
    if ":" in s:
        sec = 0.0
        for part in s.split(":"):
            sec = sec * 60 + float(part)
        return sec
    return float(s)


def build_trim(ss: float | None, to: float | None) -> str:
    """Filtergraph prefix keeping only [ss, to) seconds with reset timestamps;
    empty when no trim. Placed first in the chain so palettegen and paletteuse
    see the identical segment."""
    if ss is None and to is None:
        return ""
    parts = []
    if ss is not None:
        parts.append(f"start={ss:g}")
    if to is not None:
        parts.append(f"end={to:g}")
    return f"trim={':'.join(parts)},setpts=PTS-STARTPTS,"


def content_sizes(canvas: int, fracs: tuple[float, ...]) -> list[int]:
    return sorted({max(16, int(round(canvas * f))) for f in fracs})
