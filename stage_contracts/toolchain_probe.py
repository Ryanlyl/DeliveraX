from __future__ import annotations

import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from typing import Any

_CACHE: dict[str, Any] | None = None
_CACHE_AT: float = 0.0


def _cache_ttl_seconds() -> float:
    raw = (os.getenv("DELIVERAX_TOOLCHAIN_CACHE_TTL_SECONDS") or "").strip()
    if not raw:
        return 15.0
    try:
        return max(1.0, float(raw))
    except ValueError:
        return 15.0


def _probe_cmd(name: str) -> dict[str, Any]:
    path = shutil.which(name)
    available = bool(path)
    version: str | None = None
    error: str | None = None
    if available:
        try:
            proc = subprocess.run(
                [name, "--version"],
                capture_output=True,
                text=True,
                timeout=2.0,
                encoding="utf-8",
                errors="replace",
            )
            out = (proc.stdout or "").strip()
            err = (proc.stderr or "").strip()
            if proc.returncode == 0 and out:
                version = out.splitlines()[0]
            elif proc.returncode == 0 and err:
                version = err.splitlines()[0]
            else:
                error = f"version command exit {proc.returncode}"
        except Exception as exc:  # pragma: no cover - defensive
            error = str(exc)
    return {
        "name": name,
        "available": available,
        "path": path or "",
        "version": version or "",
        "error": error or "",
    }


def probe_js_toolchain(*, force_refresh: bool = False) -> dict[str, Any]:
    global _CACHE, _CACHE_AT
    now = time.monotonic()
    if not force_refresh and _CACHE is not None and now - _CACHE_AT <= _cache_ttl_seconds():
        return dict(_CACHE)

    node = _probe_cmd("node")
    npm = _probe_cmd("npm")
    npx = _probe_cmd("npx")
    pnpm = _probe_cmd("pnpm")
    yarn = _probe_cmd("yarn")

    package_manager_available = bool(npm["available"] or pnpm["available"] or yarn["available"])
    recommended = "npm" if npm["available"] else ("pnpm" if pnpm["available"] else ("yarn" if yarn["available"] else ""))

    payload: dict[str, Any] = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "ok" if node["available"] and package_manager_available else "degraded",
        "node_available": bool(node["available"]),
        "package_manager_available": package_manager_available,
        "recommended_package_manager": recommended,
        "tools": {
            "node": node,
            "npm": npm,
            "npx": npx,
            "pnpm": pnpm,
            "yarn": yarn,
        },
    }
    _CACHE = dict(payload)
    _CACHE_AT = now
    return payload
