"""Size-budget search, format-agnostic: given any encode(fps)->bytes callable,
find the highest fps that fits, then pick one candidate per --priority.
Ported from gif_compressor (docs/references/external_repos/gif_compressor)."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable


def byte_ceiling(target_kb: float) -> int:
    """Safe byte budget: satisfies both KB(1000) and KiB(1024) readings, minus
    a little headroom; floored so tiny budgets stay sane."""
    return max(int(min(target_kb * 1000, target_kb * 1024) - 4096), 20_000)


@dataclass
class FitResult:
    label: str
    width: int
    height: int
    fps: float
    frames: int
    size: int
    path: str
    key: int = 0   # effective artwork/content resolution (priority selection)


def fit_fps(encode: Callable[[float], int], src_fps: float, min_fps: float,
            target: int) -> tuple[float, int] | None:
    """Highest fps whose encoded size <= target (proportional search; size is
    ~linear in fps). Returns (fps, size) or None when nothing fits."""
    best: tuple[float, int] | None = None

    def attempt(fps: float) -> int:
        nonlocal best
        fps = max(min_fps, min(src_fps, fps))
        size = encode(fps)
        if size <= target and (best is None or fps > best[0]):
            best = (fps, size)
        return size

    size = attempt(src_fps)
    if size > target:
        fps = src_fps
        for _ in range(5):
            fps = max(min_fps, min(src_fps, fps * (target * 0.97) / size))
            size = attempt(fps)
            if 0.90 * target <= size <= target:
                break
            if fps <= min_fps and size > target:
                break
    return best


def choose(results: list[FitResult], priority: str) -> FitResult:
    """frames -> smallest content (most frames / smoothest); resolution ->
    largest content (biggest artwork); balanced -> nearest the geometric mean
    of feasible content sizes."""
    rs = sorted(results, key=lambda r: r.key)
    if priority == "frames":
        return rs[0]
    if priority == "resolution":
        return rs[-1]
    logmean = sum(math.log(r.key) for r in rs) / len(rs)
    return min(rs, key=lambda r: abs(math.log(r.key) - logmean))
