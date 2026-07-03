"""Environment-driven configuration. No secrets here; all values are
non-sensitive operational defaults, overridable via DCM_* env vars."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    host: str = field(default_factory=lambda: _env("DCM_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(_env("DCM_PORT", "8000")))
    max_upload_mb: int = field(
        default_factory=lambda: int(_env("DCM_MAX_UPLOAD_MB", "32")))
    data_dir: str = field(default_factory=lambda: _env("DCM_DATA_DIR", "./data"))

    # external tool overrides (empty -> resolve from PATH)
    ffmpeg: str = field(default_factory=lambda: _env("DCM_FFMPEG", ""))
    ffprobe: str = field(default_factory=lambda: _env("DCM_FFPROBE", ""))
    gifsicle: str = field(default_factory=lambda: _env("DCM_GIFSICLE", ""))
    rsvg_convert: str = field(
        default_factory=lambda: _env("DCM_RSVG_CONVERT", ""))
    pngquant: str = field(default_factory=lambda: _env("DCM_PNGQUANT", ""))

    # animated-SVG capture
    capture_fps: float = field(
        default_factory=lambda: float(_env("DCM_CAPTURE_FPS", "24")))
    capture_max_seconds: float = field(
        default_factory=lambda: float(_env("DCM_CAPTURE_MAX_SECONDS", "15")))
    default_duration: float = field(
        default_factory=lambda: float(_env("DCM_DEFAULT_DURATION", "3")))


def load_settings() -> Settings:
    return Settings()
