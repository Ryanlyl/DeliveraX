from __future__ import annotations

from fastapi import APIRouter
from stage_contracts import probe_js_toolchain, snapshot_codetest_metrics

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    probe = probe_js_toolchain()
    return {"status": "ok", "js_toolchain": probe, "codetest_metrics": snapshot_codetest_metrics()}
