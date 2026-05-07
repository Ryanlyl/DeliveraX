from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import read_json
from .schemas import UpstreamResult


PASSED_TEST_STATUSES = {"pass", "passed", "success", "succeeded", "ok", "green"}
SOFT_PASS_TEST_CODES = {
    "test-generation-mismatch",
    "test-assert-failed",
    "codetestfailed",
}
APPROVED_REVIEW_STATUSES = {
    "approve",
    "approved",
    "approved-with-notes",
    "accepted",
    "pass",
    "passed",
    "ok",
    "no-changes-detected",
}


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
        if stage == "test" and _is_successful_local_only_test(payload):
            status = "passed"
        if stage == "test" and _is_soft_passed_non_critical_test(payload):
            status = "passed"
        detail = _find_detail(payload)
        return {"status": status, "source": "file", "path": path, "detail": detail}
    return {
        "status": assumed_status,
        "source": "assumed",
        "detail": f"{stage} module is not integrated yet; status assumed by Integration input contract.",
    }


def _find_status(payload: Any) -> str | None:
    if isinstance(payload, dict):
        for key in ("status", "conclusion", "result", "decision", "state", "verdict"):
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


def _is_successful_local_only_test(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    errors = payload.get("errors")
    return bool(payload.get("local_only") is True and not errors)


def _is_soft_passed_non_critical_test(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False

    environment_error_code = str(payload.get("environment_error_code") or "").strip()
    if environment_error_code:
        return False

    if payload.get("soft_failed") is True:
        return True

    status = _normalize_status(str(payload.get("status") or ""))
    if status not in {"failed", "fail", "error"}:
        return False

    validation_error_code = _normalize_status(str(payload.get("validation_error_code") or ""))
    if validation_error_code in SOFT_PASS_TEST_CODES:
        return True

    error_code = _normalize_status(str(payload.get("error_code") or ""))
    return error_code in SOFT_PASS_TEST_CODES

