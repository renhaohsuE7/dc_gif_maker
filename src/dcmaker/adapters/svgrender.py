"""Static SVG rasteriser. Prefers rsvg-convert (librsvg, best fidelity for
static SVG); falls back to cairosvg when installed. Business logic only calls
render_png()."""
from __future__ import annotations

from .tools import ToolError, find_tool, run


class SvgRenderer:
    def __init__(self, rsvg_convert: str = ""):
        self.rsvg = find_tool("rsvg-convert", rsvg_convert)
        if not self.rsvg:
            try:
                import cairosvg  # noqa: F401
                self._cairosvg = True
            except ImportError:
                raise ToolError(
                    "no SVG renderer: install librsvg2-bin (rsvg-convert) "
                    "or `pip install cairosvg`")
        else:
            self._cairosvg = False

    def render_png(self, svg_path: str, out_png: str, box: int) -> None:
        """Rasterise fitting inside a box x box square, keeping aspect ratio,
        transparent background."""
        if self.rsvg:
            run([self.rsvg, "-w", str(box), "-h", str(box),
                 "--keep-aspect-ratio", "--format", "png",
                 "-o", out_png, svg_path], check=True)
        else:
            import cairosvg
            cairosvg.svg2png(url=svg_path, write_to=out_png,
                             output_width=box, output_height=box)
