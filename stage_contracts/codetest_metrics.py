from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any

_LOCK = Lock()
_METRICS: dict[str, Any] = {
    "preflight_fail_count": 0,
    "preflight_fail_by_code": {},
    "pm_fallback_count": 0,
    "pm_fallback_by_target": {},
    "pm_fallback_blocked_count": 0,
    "dep_install_attempt_count": 0,
    "dep_install_fail_count": 0,
    "dep_install_duration_ms_total": 0,
    "dep_install_duration_ms_last": 0,
    "updated_at": "",
}


def reset_codetest_metrics() -> None:
    with _LOCK:
        _METRICS.update(
            {
                "preflight_fail_count": 0,
                "preflight_fail_by_code": {},
                "pm_fallback_count": 0,
                "pm_fallback_by_target": {},
                "pm_fallback_blocked_count": 0,
                "dep_install_attempt_count": 0,
                "dep_install_fail_count": 0,
                "dep_install_duration_ms_total": 0,
                "dep_install_duration_ms_last": 0,
                "updated_at": "",
            }
        )


def _touch() -> None:
    _METRICS["updated_at"] = datetime.now(timezone.utc).isoformat()


def record_preflight_failure(code: str) -> None:
    with _LOCK:
        _METRICS["preflight_fail_count"] += 1
        by_code = _METRICS["preflight_fail_by_code"]
        by_code[code] = int(by_code.get(code, 0)) + 1
        _touch()


def record_pm_fallback(target_pm: str) -> None:
    with _LOCK:
        _METRICS["pm_fallback_count"] += 1
        by_target = _METRICS["pm_fallback_by_target"]
        by_target[target_pm] = int(by_target.get(target_pm, 0)) + 1
        _touch()


def record_pm_fallback_blocked() -> None:
    with _LOCK:
        _METRICS["pm_fallback_blocked_count"] += 1
        _touch()


def record_dep_install(*, duration_ms: int, success: bool) -> None:
    with _LOCK:
        _METRICS["dep_install_attempt_count"] += 1
        if not success:
            _METRICS["dep_install_fail_count"] += 1
        _METRICS["dep_install_duration_ms_total"] += max(0, int(duration_ms))
        _METRICS["dep_install_duration_ms_last"] = max(0, int(duration_ms))
        _touch()


def snapshot_codetest_metrics() -> dict[str, Any]:
    with _LOCK:
        attempt_count = int(_METRICS["dep_install_attempt_count"])
        avg_ms = (
            int(_METRICS["dep_install_duration_ms_total"]) / attempt_count
            if attempt_count > 0
            else 0.0
        )
        return {
            **_METRICS,
            "dep_install_duration_ms_avg": avg_ms,
            "preflight_fail_by_code": dict(_METRICS["preflight_fail_by_code"]),
            "pm_fallback_by_target": dict(_METRICS["pm_fallback_by_target"]),
        }
