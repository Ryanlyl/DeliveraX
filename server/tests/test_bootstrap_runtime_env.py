from __future__ import annotations

from pathlib import Path

from api_server import bootstrap


def test_configure_runtime_env_sets_bin_and_path(monkeypatch) -> None:
    monkeypatch.delenv("CODETEST_NODE_BIN_DIR", raising=False)
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setattr(bootstrap, "_discover_node_bin_dir", lambda: Path("/opt/node/bin"))

    bootstrap.configure_runtime_env()

    configured = Path(bootstrap.os.environ.get("CODETEST_NODE_BIN_DIR", "")).as_posix()
    first_path = Path(bootstrap.os.environ.get("PATH", "").split(bootstrap.os.pathsep)[0]).as_posix()
    assert configured.endswith("/opt/node/bin")
    assert first_path.endswith("/opt/node/bin")


def test_configure_runtime_env_respects_existing_bindir(monkeypatch) -> None:
    monkeypatch.setenv("CODETEST_NODE_BIN_DIR", "/custom/node/bin")
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setattr(bootstrap, "_discover_node_bin_dir", lambda: Path("/opt/node/bin"))

    bootstrap.configure_runtime_env()

    configured = Path(bootstrap.os.environ.get("CODETEST_NODE_BIN_DIR", "")).as_posix()
    first_path = Path(bootstrap.os.environ.get("PATH", "").split(bootstrap.os.pathsep)[0]).as_posix()
    assert configured.endswith("/custom/node/bin")
    assert first_path.endswith("/custom/node/bin")
