"""Pure-function unit tests — no external tools, always runnable."""
import os
import tempfile

import pytest

import dcmaker.core.service as service
from dcmaker.core.animate import webp_info
from dcmaker.core.budget import (FitResult, byte_ceiling, choose, fit_fps,
                                 fit_strategy)
from dcmaker.core.detect import detect_kind
from dcmaker.core.geometry import (build_trim, content_sizes, geom_square,
                                   parse_time)
from dcmaker.core.service import (ConvertRequest, convert, convert_all,
                                  convert_many, derive_out, is_batch_input,
                                  iter_inputs, resolve_format)
from dcmaker.presets import DEFAULT_STRATEGY, PRESETS, STRATEGIES


# ------------------------------------------------------------------ budget
def test_byte_ceiling_uses_stricter_kb_reading():
    assert byte_ceiling(512) == 512 * 1000 - 4096
    assert byte_ceiling(1) == 20_000  # floor for tiny budgets


def _r(key, frames=10):
    return FitResult(str(key), key, key, 10.0, frames, 1000, "x", key)


def test_choose_priorities():
    rs = [_r(100, frames=30), _r(200, frames=20), _r(400, frames=10)]
    assert choose(rs, "frames").key == 100      # most frames wins
    assert choose(rs, "resolution").key == 400  # biggest artwork wins
    assert choose(rs, "balanced").key == 200    # geometric mean of 100..400


def test_choose_frames_tiebreak_prefers_bigger_artwork():
    # a short loop that keeps ALL frames at every size -> bigger is free
    rs = [_r(100, frames=48), _r(200, frames=48), _r(400, frames=48)]
    assert choose(rs, "frames").key == 400


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


# --------------------------------------------------------------- strategies
def test_fit_strategy_colors_first_keeps_src_fps():
    # size model: fps x colours bytes -> 96 is the first rung that fits
    calls = []

    def enc(fps, colors):
        calls.append((fps, colors))
        return int(fps * colors)

    got = fit_strategy(enc, 10.0, 1.0, 960, (256, 192, 128, 96, 64), True)
    assert got == (10.0, 96, 960)                 # source fps preserved
    assert calls == [(10.0, 256), (10.0, 192), (10.0, 128), (10.0, 96)]


def test_fit_strategy_fps_falls_back_after_ladder():
    # even the smallest rung misses at full fps -> fps search at that rung
    got = fit_strategy(lambda f, c: int(f * c * 10), 10.0, 1.0, 1000,
                       (64, 32), True)
    assert got is not None
    fps, colors, size = got
    assert colors == 32 and fps < 10.0 and size <= 1000


def test_fit_strategy_single_rung_is_fps_search():
    # frames/balanced shape: one rung, proportional fps search at it
    got = fit_strategy(lambda f, c: int(f * 100), 10.0, 1.0, 500, (256,), False)
    assert got is not None
    fps, colors, size = got
    assert colors == 256 and size <= 500


def test_strategies_table():
    assert DEFAULT_STRATEGY == "balanced"       # validated 2026-07-23
    assert STRATEGIES["frames"].rungs == (256,)
    ladder = STRATEGIES["colors"].rungs
    assert ladder[0] == 256 and list(ladder) == sorted(ladder, reverse=True)
    assert STRATEGIES["colors"].pin_fps and not STRATEGIES["frames"].pin_fps
    # balanced resolves per preset: the eye-ranked palettes from the
    # strategy-matrix experiment (docs/experiments/2026-07-23-…)
    assert STRATEGIES["balanced"].rungs == ()
    assert PRESETS["sticker"].balanced_colors == 96
    assert PRESETS["emoji"].balanced_colors == 32


def test_strategy_rejected_off_gif_route(tmp_path):
    gif = tmp_path / "x.gif"
    gif.write_bytes(b"GIF89a")
    with pytest.raises(ValueError, match="GIF route"):
        convert(ConvertRequest(str(gif), fmt="webp", strategy="colors"))
    with pytest.raises(ValueError, match="strategy must be one of"):
        convert(ConvertRequest(str(gif), strategy="yolo"))


def test_convert_all_rejects_out_and_runs_every_preset(tmp_path, monkeypatch):
    gif = tmp_path / "x.gif"
    gif.write_bytes(b"GIF89a")
    with pytest.raises(ValueError, match="--out"):
        convert_all(ConvertRequest(str(gif), out="one.gif"))

    seen = []

    def fake_convert(req, settings=None, progress=None, _shared=None):
        seen.append(req.preset)
        return f"ok:{req.preset}"

    monkeypatch.setattr(service, "convert", fake_convert)
    rs = convert_all(ConvertRequest(str(gif)))
    assert seen == ["sticker", "emoji"] and len(rs) == 2


# -------------------------------------------------------------------- webp
def _webp_bytes(w: int, h: int, nframes: int) -> bytes:
    """Minimal animated-WebP RIFF: VP8X canvas header + N empty ANMF chunks."""
    def u24(n: int) -> bytes:
        return n.to_bytes(3, "little")
    vp8x = (b"VP8X" + (10).to_bytes(4, "little")
            + bytes([0x02, 0, 0, 0]) + u24(w - 1) + u24(h - 1))
    anmf = b"".join(b"ANMF" + (0).to_bytes(4, "little") for _ in range(nframes))
    body = b"WEBP" + vp8x + anmf
    return b"RIFF" + len(body).to_bytes(4, "little") + body


def test_webp_info_reads_canvas_and_frame_count(tmp_path):
    path = tmp_path / "x.webp"
    path.write_bytes(_webp_bytes(128, 320, 7))
    assert webp_info(str(path)) == (128, 320, 7)


def test_webp_info_rejects_non_webp(tmp_path):
    path = tmp_path / "x.webp"
    path.write_bytes(b"NOPEabcdNOPE")
    with pytest.raises(Exception):
        webp_info(str(path))


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
    assert resolve_format("gif", "webp") == "webp"          # animated -> webp
    assert resolve_format("svg-animated", "webp") == "webp"
    assert resolve_format("svg-static", "auto") == "png"
    assert resolve_format("raster", "auto") == "png"
    with pytest.raises(ValueError):
        resolve_format("svg-static", "gif")   # nothing to animate
    with pytest.raises(ValueError):
        resolve_format("svg-static", "webp")  # webp is animated-only here
    with pytest.raises(ValueError):
        resolve_format("gif", "png")          # animated -> not png


def test_derive_out_original_sibling():
    out = derive_out("/a/original/x.gif", "dc_sticker_gif", "gif")
    assert out == os.path.join("/a", "output", "x-dc_sticker_gif.gif")
    out = derive_out("/a/b/x.svg", "dc_emoji_png", "png")
    assert out == os.path.join("/a/b", "x-dc_emoji_png.png")
    assert derive_out("x.gif", "s", "gif", out="/tmp/y.gif") == "/tmp/y.gif"


# ------------------------------------------------------------------- batch
def _touch(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "wb").close()
    return path


def test_is_batch_input(tmp_path):
    f = _touch(str(tmp_path / "x.gif"))
    assert is_batch_input(str(tmp_path))          # directory
    assert is_batch_input(str(tmp_path / "*.gif"))  # glob
    assert not is_batch_input(f)                  # plain file


def test_iter_inputs_top_level_recursive_and_unsupported(tmp_path):
    _touch(str(tmp_path / "b.gif"))
    _touch(str(tmp_path / "a.svg"))
    _touch(str(tmp_path / "readme.txt"))
    _touch(str(tmp_path / "sub" / "c.gif"))
    sup, unsup = iter_inputs(str(tmp_path))
    assert [os.path.basename(p) for p in sup] == ["a.svg", "b.gif"]  # sorted
    assert [os.path.basename(p) for p in unsup] == ["readme.txt"]
    sup, _ = iter_inputs(str(tmp_path), recursive=True)
    assert {os.path.basename(p) for p in sup} == {"a.svg", "b.gif", "c.gif"}


def test_iter_inputs_glob(tmp_path):
    _touch(str(tmp_path / "a.gif"))
    _touch(str(tmp_path / "b.png"))
    sup, unsup = iter_inputs(str(tmp_path / "*.gif"))
    assert [os.path.basename(p) for p in sup] == ["a.gif"]
    assert unsup == []


def test_convert_many_guard_isolation_and_stop(monkeypatch):
    calls = []

    def fake_convert(req, settings=None, progress=None):
        calls.append(req.input_path)
        if "bad" in req.input_path:
            raise RuntimeError("boom")
        return f"ok:{req.input_path}"

    monkeypatch.setattr(service, "convert", fake_convert)

    # --out with many inputs: rejected before any conversion starts
    with pytest.raises(ValueError, match="--out"):
        convert_many(["a.gif", "b.gif"], ConvertRequest("x", out="one.gif"))
    assert calls == []

    # skip (default): the bad file is recorded, the rest still convert
    rs = convert_many(["a.gif", "bad.gif", "c.gif"], ConvertRequest("x"))
    assert [b.error is None for b in rs] == [True, False, True]
    assert "RuntimeError" in rs[1].error and rs[1].path == "bad.gif"

    # stop: aborts at the first failure, naming the file
    calls.clear()
    with pytest.raises(ValueError, match="stopped at bad.gif"):
        convert_many(["a.gif", "bad.gif", "c.gif"], ConvertRequest("x"),
                     on_error="stop")
    assert calls == ["a.gif", "bad.gif"]          # c.gif never attempted

    with pytest.raises(ValueError, match="on_error"):
        convert_many([], ConvertRequest("x"), on_error="explode")
