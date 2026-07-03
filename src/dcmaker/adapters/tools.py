"""Subprocess helpers + external tool resolution (PATH or env override)."""
from __future__ import annotations

import shutil
import subprocess


class ToolError(RuntimeError):
    """An external tool is missing or exited non-zero."""


def run(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise ToolError(
            f"{cmd[0]} failed (exit {proc.returncode}): {proc.stderr.strip()[:800]}")
    return proc


def find_tool(name: str, override: str = "") -> str:
    """Resolve a tool binary: explicit override first, then PATH. Returns ""
    when not found (callers decide whether that is fatal)."""
    if override:
        return override
    return shutil.which(name) or ""


def require_tool(name: str, override: str = "") -> str:
    path = find_tool(name, override)
    if not path:
        raise ToolError(
            f"required tool '{name}' not found on PATH "
            f"(install it or set DCM_{name.upper().replace('-', '_')})")
    return path
