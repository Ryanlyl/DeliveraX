from __future__ import annotations

from pathlib import Path

from agents.code_testing import nodes


class _FakePath:
    def __init__(self, raw: str) -> None:
        self.raw = raw

    def is_file(self) -> bool:
        return True

    def __str__(self) -> str:
        return self.raw


def test_resolve_npm_invocation_falls_back_to_npm_cli(monkeypatch) -> None:
    monkeypatch.setattr(nodes, "_resolve_cmd", lambda cmd: cmd)
    monkeypatch.setattr(nodes, "_cmd_exists", lambda cmd, env: False)
    monkeypatch.setattr(nodes, "_node_executable", lambda env: "/fake/node")
    monkeypatch.setattr(nodes, "_npm_cli_candidates", lambda node_exe: [_FakePath("/fake/npm-cli.js")])

    cmd = nodes._resolve_npm_invocation(["install"], {"PATH": ""})
    assert cmd == ["/fake/node", "/fake/npm-cli.js", "install"]


def test_subprocess_env_prepends_node_bin_candidates(monkeypatch) -> None:
    monkeypatch.setattr(nodes, "_node_bin_candidates", lambda: [Path("/opt/node/bin"), Path("/usr/bin")])
    monkeypatch.setenv("PATH", "Z:\\legacy\\bin")
    env = nodes._subprocess_env({})
    head = [part.replace("\\", "/") for part in env["PATH"].split(nodes.os.pathsep)[:2]]
    assert head == ["/opt/node/bin", "/usr/bin"]
