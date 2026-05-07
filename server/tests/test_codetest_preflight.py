from __future__ import annotations

from agents.code_testing import nodes
from agents.code_testing.stage import _derive_error_code


def test_preflight_toolchain_marks_env_pm_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        nodes,
        "_effective_toolchain_probe",
        lambda: {
            "status": "degraded",
            "node_available": True,
            "package_manager_available": False,
            "recommended_package_manager": "",
            "path_probe": {},
            "runtime_probe": {},
        },
    )
    state = {"local_only": False, "warnings": [], "errors": []}
    updated = nodes.preflight_toolchain(state)
    assert updated.get("environment_error_code") == "ENV_PM_MISSING"
    assert any("package manager" in e.lower() for e in updated.get("errors", []))


def test_preflight_toolchain_accepts_fallback_recovered_runtime(monkeypatch) -> None:
    monkeypatch.setattr(
        nodes,
        "_effective_toolchain_probe",
        lambda: {
            "status": "ok",
            "node_available": True,
            "package_manager_available": True,
            "recommended_package_manager": "npm",
            "node_recovered_by_fallback": True,
            "pm_recovered_by_fallback": True,
            "path_probe": {
                "node_available": False,
                "package_manager_available": False,
            },
            "runtime_probe": {
                "node_available": True,
                "npm_available": True,
                "pnpm_available": False,
                "yarn_available": False,
            },
        },
    )
    state = {"local_only": False, "warnings": [], "errors": []}
    updated = nodes.preflight_toolchain(state)
    assert updated.get("environment_error_code") is None
    assert not updated.get("errors")
    assert any("fallback runtime path injection" in w for w in updated.get("warnings", []))


def test_derive_error_code_prefers_environment_code() -> None:
    code = _derive_error_code(
        result_state={"environment_error_code": "ENV_NODE_MISSING"},
        summary="Dependency install failed; see test_run log.",
        legacy_status="failed",
    )
    assert code == "ENV_NODE_MISSING"


def test_derive_error_code_prefers_validation_code() -> None:
    code = _derive_error_code(
        result_state={"validation_error_code": "TEST_GENERATION_MISMATCH"},
        summary="Tests failed (exit 1). See log.",
        legacy_status="failed",
    )
    assert code == "TEST_GENERATION_MISMATCH"
