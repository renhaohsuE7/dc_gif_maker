"""Animated-SVG frame capture via headless Chromium (Playwright).

The SVG is inlined into a transparent wrapper page; SMIL and CSS/WAAPI
animations are paused and stepped deterministically (svg.setCurrentTime for
SMIL, Animation.currentTime for WAAPI), one screenshot per frame with a
transparent background. The result is a numbered PNG sequence that feeds the
same GIF/APNG budget pipeline as a GIF source."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

from .tools import ToolError

_WRAP = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;padding:0;background:transparent;overflow:hidden}}
svg:root,body>svg{{display:block;width:100vw;height:100vh}}
</style></head><body>{svg}</body></html>"""

# normalise the root <svg> so it scales to the viewport: ensure a viewBox
# (derive one from width/height when absent), then drop fixed dimensions.
_JS_NORMALISE = """() => {
  const svg = document.querySelector('svg');
  if (!svg) return 'no <svg> element';
  if (!svg.getAttribute('viewBox')) {
    const w = parseFloat(svg.getAttribute('width')) || 0;
    const h = parseFloat(svg.getAttribute('height')) || 0;
    if (w && h) svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
  }
  svg.removeAttribute('width'); svg.removeAttribute('height');
  svg.pauseAnimations();
  for (const a of document.getAnimations()) a.pause();
  return '';
}"""

# longest animation end in seconds; infinite repeats count as one cycle.
_JS_DURATION = """() => {
  let max = 0;
  for (const a of document.getAnimations()) {
    const t = a.effect.getComputedTiming();
    const total = t.iterations === Infinity
      ? t.duration : t.duration * t.iterations;
    const end = (Number(t.delay) + Number(total)) / 1000;
    if (isFinite(end)) max = Math.max(max, end);
  }
  const clock = (s) => {
    if (!s) return 0;
    s = s.trim();
    if (/^[0-9.]+ms$/.test(s)) return parseFloat(s) / 1000;
    if (/^[0-9.]+s?$/.test(s)) return parseFloat(s);
    if (/^[0-9:.]+$/.test(s))
      return s.split(':').reduce((acc, p) => acc * 60 + parseFloat(p), 0);
    return 0;
  };
  const svg = document.querySelector('svg');
  for (const el of svg.querySelectorAll(
      'animate,animateTransform,animateMotion,set')) {
    const dur = clock(el.getAttribute('dur'));
    if (!dur) continue;
    const begin = clock(el.getAttribute('begin'));
    const repDur = clock(el.getAttribute('repeatDur'));
    const reps = el.getAttribute('repeatCount');
    const total = repDur ? repDur
      : (!reps || reps === 'indefinite') ? dur : dur * parseFloat(reps);
    max = Math.max(max, begin + total);
  }
  return max;
}"""

_JS_SEEK = """(t) => {
  document.querySelector('svg').setCurrentTime(t);
  for (const a of document.getAnimations()) a.currentTime = t * 1000;
}"""


@dataclass(frozen=True)
class Capture:
    frames_dir: str
    frames: int
    fps: float
    duration: float


def capture_svg_frames(svg_path: str, frames_dir: str, box: int, fps: float,
                       duration: float | None, default_duration: float,
                       max_seconds: float) -> Capture:
    """Capture `duration` seconds (auto-detected when None) at `fps` into
    frames_dir/frame_%05d.png, each frame box x box with transparency."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ToolError("playwright not installed: pip install playwright && "
                        "playwright install chromium") from exc

    svg_text = open(svg_path, encoding="utf-8").read()
    # the wrapper inlines the SVG; strip any XML prolog/doctype
    svg_text = re.sub(r"<\?xml[^>]*\?>|<!DOCTYPE[^>]*>", "", svg_text)
    os.makedirs(frames_dir, exist_ok=True)
    wrapper = os.path.join(frames_dir, "_wrap.html")
    with open(wrapper, "w", encoding="utf-8") as fh:
        fh.write(_WRAP.format(svg=svg_text))

    launch_args = ["--force-color-profile=srgb", "--hide-scrollbars",
                   "--disable-dev-shm-usage"]
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        # containers run us as root; Chromium's sandbox cannot start there
        launch_args.append("--no-sandbox")

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(args=launch_args)
        except Exception as exc:
            raise ToolError(
                f"chromium launch failed (run `playwright install "
                f"--with-deps chromium`): {exc}") from exc
        try:
            page = browser.new_page(
                viewport={"width": box, "height": box},
                device_scale_factor=1)
            page.goto("file://" + os.path.abspath(wrapper))
            err = page.evaluate(_JS_NORMALISE)
            if err:
                raise ToolError(f"invalid SVG: {err}")
            if duration is None:
                duration = float(page.evaluate(_JS_DURATION)) or default_duration
            duration = min(duration, max_seconds)
            n = max(2, round(duration * fps))
            for i in range(n):
                page.evaluate(_JS_SEEK, i / fps)
                page.screenshot(
                    path=os.path.join(frames_dir, f"frame_{i:05d}.png"),
                    omit_background=True)
        finally:
            browser.close()
    os.remove(wrapper)
    return Capture(frames_dir, n, fps, duration)
