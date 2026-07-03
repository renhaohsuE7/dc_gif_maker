"""Input-type detection: what did the user hand us, and does it move?"""
from __future__ import annotations

import os
import re

# SMIL elements, CSS animation/transition properties, or @keyframes blocks
_SVG_ANIM = re.compile(
    r"<(?:animate|animateTransform|animateMotion|set)[\s>]"
    r"|@keyframes"
    r"|animation(?:-name)?\s*:"
    r"|<script", re.IGNORECASE)

RASTER_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def detect_kind(path: str) -> str:
    """Returns one of: 'svg-animated', 'svg-static', 'gif', 'raster'."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".svg":
        try:
            head = open(path, encoding="utf-8", errors="replace").read(512_000)
        except OSError:
            head = ""
        return "svg-animated" if _SVG_ANIM.search(head) else "svg-static"
    if ext == ".gif":
        return "gif"
    if ext in RASTER_EXTS:
        return "raster"
    raise ValueError(f"unsupported input type: {ext or path}"
                     " (supported: .svg .gif .png .jpg .webp)")
