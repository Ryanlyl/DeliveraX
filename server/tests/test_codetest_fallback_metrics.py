from __future__ import annotations

from pathlib import Path

from agents.code_testing import nodes
from stage_contracts import reset_codetest_metrics, snapshot_codetest_metrics


def test_install_respects_fallback_switch_disabled(monkeypatch) -> None:
    reset_codetest_metrics()
    monkeypatch.setenv("CODETEST_ALLOW_PM_FALLBACK", "false")
    monkeypatch.setattr(nodes, "_subprocess_env", lambda extra=None: {})
    monkeypatch.setattr(nodes, "_resolve_npm_invocation", lambda args, env: None)
    monkeypatch.setattr(nodes, "_resolve_cmd", lambda cmd: cmd)
    monkeypatch.setattr(nodes, "_cmd_exists", lambda cmd, env: False)
    monkeypatch.setattr(nodes, "_node_bin_candidates", lambda: [Path("/usr/local/bin"), Path("/usr/bin")])

    logs: list[str] = []
    ok = nodes._install_dependencies(Path("."), ["npm"], logs)
    assert ok is False
    assert any("CODETEST_ALLOW_PM_FALLBACK=false" in line for line in logs)

    metrics = snapshot_codetest_metrics()
    assert metrics["pm_fallback_blocked_count"] >= 1
    assert metrics["dep_install_attempt_count"] >= 1
    assert metrics["dep_install_fail_count"] >= 1


def test_install_records_fallback_to_pnpm(monkeypatch) -> None:
    class _Proc:
        returncode = 0
        stdout = "ok"
        stderr = ""

    reset_codetest_metrics()
    monkeypatch.setenv("CODETEST_ALLOW_PM_FALLBACK", "true")
    monkeypatch.setattr(nodes, "_subprocess_env", lambda extra=None: {})
    monkeypatch.setattr(nodes, "_resolve_npm_invocation", lambda args, env: None)
    monkeypatch.setattr(nodes, "_resolve_cmd", lambda cmd: cmd)
    monkeypatch.setattr(nodes, "_cmd_exists", lambda cmd, env: bool(cmd and cmd[0] == "pnpm"))
    monkeypatch.setattr(nodes.subprocess, "run", lambda *args, **kwargs: _Proc())

    logs: list[str] = []
    ok = nodes._install_dependencies(Path("."), ["npm"], logs)
    assert ok is True
    assert any("fallback to pnpm install" in line for line in logs)

    metrics = snapshot_codetest_metrics()
    assert metrics["pm_fallback_count"] >= 1
    assert int(metrics["pm_fallback_by_target"].get("pnpm", 0)) >= 1
    assert metrics["dep_install_attempt_count"] >= 1
