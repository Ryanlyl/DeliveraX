from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _candidate_node_bin_dirs() -> list[Path]:
    candidates: list[Path] = []
    direct = (os.getenv("CODETEST_NODE_BIN_DIR") or "").strip()
    if direct:
        candidates.append(Path(direct))
    for env_name in ("NODE_HOME", "NODEJS_HOME"):
        value = (os.getenv(env_name) or "").strip()
        if not value:
            continue
        base = Path(value)
        candidates.append(base)
        candidates.append(base / "bin")
    located = shutil.which("node.exe") or shutil.which("node")
    if located:
        candidates.append(Path(located).resolve().parent)
    if os.name == "nt":
        candidates.extend(
            [
                Path(r"C:\Program Files\nodejs"),
                Path(r"C:\Program Files (x86)\nodejs"),
                Path(r"C:\nodejs"),
            ]
        )
    else:
        candidates.extend([Path("/usr/local/bin"), Path("/usr/bin"), Path("/opt/node/bin")])

    seen: set[str] = set()
    result: list[Path] = []
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def _discover_node_bin_dir() -> Path | None:
    node_name = "node.exe" if os.name == "nt" else "node"
    for bindir in _candidate_node_bin_dirs():
        try:
            candidate = bindir.resolve()
        except OSError:
            candidate = bindir
        if (candidate / node_name).is_file():
            return candidate
    return None


def configure_runtime_env() -> None:
    discovered = _discover_node_bin_dir()
    if discovered and not (os.getenv("CODETEST_NODE_BIN_DIR") or "").strip():
        os.environ["CODETEST_NODE_BIN_DIR"] = str(discovered)

    node_bin = (os.getenv("CODETEST_NODE_BIN_DIR") or "").strip()
    if not node_bin:
        return
    path_sep = os.pathsep
    path_items = [item for item in os.getenv("PATH", "").split(path_sep) if item]
    if node_bin not in path_items:
        os.environ["PATH"] = path_sep.join([node_bin, *path_items])


def ensure_repo_paths(root: Path | None = None) -> Path:
    configure_runtime_env()
    resolved_root = (root or repo_root()).resolve()
    candidates = [resolved_root]
    agents_dir = resolved_root / "agents"
    if agents_dir.is_dir():
        candidates.append(agents_dir)
        for entry in sorted(agents_dir.iterdir()):
            if entry.is_dir() and not entry.name.startswith("."):
                candidates.append(entry)
    for path in candidates:
        text = str(path)
        if path.exists() and text not in sys.path:
            sys.path.insert(0, text)
    return resolved_root
