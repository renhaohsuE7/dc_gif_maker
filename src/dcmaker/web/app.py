"""Transport layer: validate the upload, delegate to core.service.convert,
serve results. No business logic here."""
from __future__ import annotations

import os
import re
import uuid

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .. import __version__
from ..config import load_settings
from ..core.service import FORMATS, ConvertRequest, convert, convert_all
from ..presets import PRESETS, PRIORITIES, STRATEGIES

settings = load_settings()
UPLOAD_DIR = os.path.join(settings.data_dir, "uploads")
OUT_DIR = os.path.join(settings.data_dir, "out")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

ALLOWED_EXTS = {".gif", ".svg", ".png", ".jpg", ".jpeg", ".webp"}
_SAFE_NAME = re.compile(r"^[a-f0-9]{32}-dc_[a-z]+_[a-z]+\.(gif|png|webp)$")
_MEDIA = {"gif": "image/gif", "webp": "image/webp", "png": "image/png"}

app = FastAPI(title="dcmaker", version=__version__)


@app.post("/api/convert")
def api_convert(file: UploadFile = File(...),
                preset: str = Form("sticker"),
                fmt: str = Form("auto"),
                priority: str = Form(""),
                strategy: str = Form(""),
                ss: str = Form(""),
                to: str = Form(""),
                duration: str = Form("")):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(415, f"unsupported file type {ext!r}")
    if preset not in PRESETS and preset != "all":
        raise HTTPException(422,
                            f"preset must be one of {(*PRESETS, 'all')}")
    if fmt not in FORMATS:
        raise HTTPException(422, f"format must be one of {FORMATS}")
    if priority and priority not in PRIORITIES:
        raise HTTPException(422, f"priority must be one of {PRIORITIES}")
    if strategy and strategy not in STRATEGIES:
        raise HTTPException(422, f"strategy must be one of {tuple(STRATEGIES)}")
    dur: float | None = None
    if duration:
        try:
            dur = float(duration)
        except ValueError:
            raise HTTPException(422, "duration must be a number (seconds)")
        if not 0 < dur <= settings.capture_max_seconds:
            raise HTTPException(
                422, f"duration must be 0-{settings.capture_max_seconds:g}s")

    job = uuid.uuid4().hex
    upload_path = os.path.join(UPLOAD_DIR, f"{job}{ext}")
    limit = settings.max_upload_mb * 1024 * 1024
    written = 0
    with open(upload_path, "wb") as fh:
        while chunk := file.file.read(1 << 20):
            written += len(chunk)
            if written > limit:
                fh.close()
                os.remove(upload_path)
                raise HTTPException(
                    413, f"file exceeds {settings.max_upload_mb}MB limit")
            fh.write(chunk)

    req = ConvertRequest(
        input_path=upload_path, preset=preset, fmt=fmt,
        priority=priority or None, strategy=strategy or None,
        ss=ss or None, to=to or None, duration=dur, out_dir=OUT_DIR)
    try:
        rs = (convert_all(req, settings) if preset == "all"
              else [convert(req, settings)])
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    finally:
        if os.path.isfile(upload_path):
            os.remove(upload_path)

    return {"results": [{
        "file": f"/files/{os.path.basename(r.path)}",
        "filename": os.path.basename(r.path),
        "format": r.fmt, "kind": r.kind, "preset": r.preset,
        "size": r.size, "width": r.width, "height": r.height,
        "frames": r.frames, "fps": r.fps, "artwork_px": r.artwork_px,
        "colors": r.colors, "budget_kb": PRESETS[r.preset].target_kb,
        "notes": r.notes,
    } for r in rs]}


@app.get("/files/{name}")
def get_file(name: str):
    if not _SAFE_NAME.match(name):
        raise HTTPException(404)
    path = os.path.join(OUT_DIR, name)
    if not os.path.isfile(path):
        raise HTTPException(404)
    media = _MEDIA.get(name.rsplit(".", 1)[-1], "image/png")
    return FileResponse(path, media_type=media, filename=name)


app.mount("/", StaticFiles(
    directory=os.path.join(os.path.dirname(__file__), "static"),
    html=True), name="static")
