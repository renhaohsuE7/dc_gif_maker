"""Pure-function unit tests — no external tools, always runnable."""
import os
import tempfile

import pytest

from dcmaker.core.budget import FitResult, byte_ceiling, choose, fit_fps
from dcmaker.core.detect import detect_kind
from dcmaker.core.geometry import (build_trim, content_sizes, geom_square,
                                   parse_time)
from dcmaker.core.service import derive_out, resolve_format


# ------------------------------------------------------------------ budget
def test_byte_ceiling_uses_stricter_kb_reading():
    assert byte_ceiling(512) == 512 * 1000 - 4096
    assert byte_ceiling(1) == 20_000  # floor for tiny budgets


def _r(key, fps=10.0):
    return FitResult(str(key), key, key, fps, 10, 1000, "x", key)


def test_choose_priorities():
    rs = [_r(100), _r(200), _r(400)]
    assert choose(rs, "frames").key == 100
    assert choose(rs, "resolution").key == 400
    assert choose(rs, "balanced").key == 200  # geometric mean of 100..400


def test_fit_fps_finds_highest_fitting_fps():
    # size model: 100 bytes per fps -> target 500 fits fps<=5
    calls = []

    def encode(fps):
        calls.append(fps)
        return int(fps * 100)

    best = fit_fps(encode, src_fps=10.0, min_fps=1.0, target=500)
    assert best is not None
    fps, size = best
    assert size <= 500
    assert fps == pytest.approx(4.85, abs=0.3)  # ~ target*0.97/size ratio


def test_fit_fps_returns_none_when_nothing_fits():
    assert fit_fps(lambda f: 10_000_000, 10.0, 2.0, 500_000) is None


# ---------------------------------------------------------------- geometry
def test_parse_time():
    assert parse_time("2.5") == 2.5
    assert parse_time("1:30") == 90
    assert parse_time("01:02:03") == 3723


def test_build_trim():
    assert build_trim(None, None) == ""
    assert build_trim(1.0, 5.0) == "trim=start=1:end=5,setpts=PTS-STARTPTS,"
    assert build_trim(None, 5.0) == "trim=end=5,setpts=PTS-STARTPTS,"


def test_geom_square_pads_to_exact_canvas():
    g = geom_square(320, 141)
    assert "scale=141:141" in g and "pad=320:320" in g and "black@0.0" in g


def test_content_sizes_dedup_and_floor():
    assert content_sizes(128, (1.0, 1.0)) == [128]
    assert content_sizes(100, (0.1, 0.5)) == [16, 50]


# ------------------------------------------------------------------ detect
def _svg_file(tmp, body):
    path = os.path.join(tmp, "x.svg")
    with open(path, "w") as fh:
        fh.write(f'<svg xmlns="http://www.w3.org/2000/svg">{body}</svg>')
    return path


def test_detect_svg_static_vs_animated():
    with tempfile.TemporaryDirectory() as tmp:
        assert detect_kind(_svg_file(tmp, "<circle r='5'/>")) == "svg-static"
        assert detect_kind(_svg_file(
            tmp, "<circle r='5'><animate attributeName='r'/></circle>")) \
            == "svg-animated"
        assert detect_kind(_svg_file(
            tmp, "<style>@keyframes x{}</style>")) == "svg-animated"


def test_detect_rejects_unknown_ext():
    with pytest.raises(ValueError):
        detect_kind("x.bmp")


# ----------------------------------------------------------------- service
def test_resolve_format_routing():
    assert resolve_format("gif", "auto") == "gif"
    assert resolve_format("svg-animated", "apng") == "apng"
    assert resolve_format("svg-static", "auto") == "png"
    assert resolve_format("raster", "auto") == "png"
    with pytest.raises(ValueError):
        resolve_format("svg-static", "gif")   # nothing to animate
    with pytest.raises(ValueError):
        resolve_format("gif", "png")          # animated -> not png


def test_derive_out_original_sibling():
    out = derive_out("/a/original/x.gif", "dc_sticker_gif", "gif")
    assert out == os.path.join("/a", "output", "x-dc_sticker_gif.gif")
    out = derive_out("/a/b/x.svg", "dc_emoji_png", "png")
    assert out == os.path.join("/a/b", "x-dc_emoji_png.png")
    assert derive_out("x.gif", "s", "gif", out="/tmp/y.gif") == "/tmp/y.gif"
