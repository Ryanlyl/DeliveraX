from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import read_json
from .schemas import UpstreamResult


PASSED_TEST_STATUSES = {"pass", "passed", "success", "succeeded", "ok", "green"}
APPROVED_REVIEW_STATUSES = {"approve", "approved", "accepted", "pass", "passed", "ok"}


def load_test_result(*, result_path: str | None, explicit_status: str | None) -> UpstreamResult:
    return _load_upstream_result(
        result_path=result_path,
        explicit_status=explicit_status,
        assumed_status="passed",
        stage="test",
    )


def load_review_result(*, result_path: str | None, explicit_status: str | None) -> UpstreamResult:
    return _load_upstream_result(
        result_path=result_path,
        explicit_status=explicit_status,
        assumed_status="approved",
        stage="review",
    )


def assert_test_passed(result: UpstreamResult) -> None:
    normalized = _normalize_status(result.get("status", ""))
    if normalized not in PASSED_TEST_STATUSES:
        raise RuntimeError(f"Upstream code test is not passed: {result.get('status', '')}")


def assert_review_approved(result: UpstreamResult) -> None:
    normalized = _normalize_status(result.get("status", ""))
    if normalized not in APPROVED_REVIEW_STATUSES:
        raise RuntimeError(f"Upstream code review is not approved: {result.get('status', '')}")


def _load_upstream_result(
    *,
    result_path: str | None,
    explicit_status: str | None,
    assumed_status: str,
    stage: str,
) -> UpstreamResult:
    if explicit_status:
        return {"status": explicit_status, "source": "cli"}
    if result_path:
        path = str(Path(result_path).resolve())
        payload = read_json(path)
        status = _find_status(payload) or ""
        detail = _find_detail(payload)
        return {"status": status, "source": "file", "path": path, "detail": detail}
    return {
        "status": assumed_status,
        "source": "assumed",
        "detail": f"{stage} module is not integrated yet; status assumed by DeliveryIntegration input contract.",
    }


def _find_status(payload: Any) -> str | None:
    if isinstance(payload, dict):
        for key in ("status", "conclusion", "result", "decision", "state"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for key in ("test", "review", "summary", "gate", "quality_gate"):
            nested = payload.get(key)
            found = _find_status(nested)
            if found:
                return found
        for value in payload.values():
            found = _find_status(value)
            if found:
                return found
    if isinstance(payload, list):
        for item in payload:
            found = _find_status(item)
            if found:
                return found
    return None


def _find_detail(payload: Any) -> str:
    if isinstance(payload, dict):
        for key in ("summary", "detail", "message", "notes"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _normalize_status(value: str) -> str:
    return value.strip().lower().replace("_", "-")

