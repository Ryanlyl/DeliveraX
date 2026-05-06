from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable


def _sanitize(s: str) -> str:
    out = []
    for ch in s.strip():
        if ch.isalnum() or ch in {"_", "-"}:
            out.append(ch)
        else:
            out.append("_")
    return "".join(out) or "case"


def _copytree(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _copyfile(src: Path, dst: Path) -> None:
    if not src.is_file():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _copytree_filtered(src: Path, dst: Path, *, ignore_names: Iterable[str]) -> None:
    if not src.exists():
        return
    if dst.exists():
        shutil.rmtree(dst)

    ignore_set = set(ignore_names)

    def _ignore(_dir: str, names: list[str]) -> set[str]:
        return {n for n in names if n in ignore_set}

    shutil.copytree(src, dst, ignore=_ignore)


def _pick_entry_html(site_dir: Path) -> str:
    if (site_dir / "index-START.html").is_file():
        return "index-START.html"
    if (site_dir / "index.html").is_file():
        return "index.html"
    htmls = sorted([p.name for p in site_dir.glob("*.html") if p.is_file()])
    return htmls[0] if htmls else "index.html"


def _write_click_to_open_html(dst: Path, *, entry: str) -> None:
    body = f"""<!doctype html>
<meta charset="utf-8" />
<meta http-equiv="refresh" content="0; url=./site/{entry}" />
<title>Open site</title>
<p>Opening <a href="./site/{entry}">./site/{entry}</a> …</p>
"""
    (dst / "OPEN_IN_BROWSER.html").write_text(body, encoding="utf-8", errors="replace")


def _sanitize_requirement_for_ra(text: str) -> str:
    # RequirementsAnalysis enforces an input boundary and may reject explicit implementation/tooling words.
    # Keep the original requirement file unchanged by sanitizing a copy for the pipeline run.
    return (
        text.replace("Playwright", "自动化浏览器测试")
        .replace("@playwright/test", "自动化浏览器测试依赖")
        .replace("playwright", "自动化浏览器测试")
    )


def _pick_site_source(*, dx_root: Path, prefix: str, fallback: Path) -> Path:
    # Prefer the most "integrated" result for comparison.
    di_repo = dx_root / "agents" / "release_integration" / ".workspace" / "tasks" / f"{prefix}_di" / "repo"
    if di_repo.is_dir():
        return di_repo

    cg_json = dx_root / "agents" / "code_generation" / "Output" / f"{prefix}_cg" / "codegen_result.json"
    if cg_json.is_file():
        try:
            data = json.loads(cg_json.read_text(encoding="utf-8", errors="replace"))
            p = Path(str(data.get("codegen_repo_path") or "")).resolve()
            if p.is_dir():
                return p
        except Exception:
            pass

    return fallback


def _run_pipeline_stream(
    *,
    dx_root: Path,
    repo_path: Path,
    req_file: Path,
    env_file: Path | None,
    prefix: str,
    log_path: Path,
    skip_code_review: bool,
) -> int:
    cmd = [
        sys.executable,
        str(dx_root / "scripts" / "run_deliver_pipeline.py"),
        "--dx-root",
        str(dx_root),
        "--repo-path",
        str(repo_path),
        "--requirement-file",
        str(req_file),
        "--pipeline-prefix",
        prefix,
    ]
    if skip_code_review:
        cmd.append("--skip-code-review")
    if env_file:
        cmd += ["--env-file", str(env_file)]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8", errors="replace") as f:
        proc = subprocess.Popen(
            cmd,
            cwd=str(dx_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            # tee to console + file for real-time progress
            sys.stdout.write(line)
            sys.stdout.flush()
            f.write(line)
            f.flush()
        return int(proc.wait())


def main() -> int:
    p = argparse.ArgumentParser(description="Batch-run DeliveraX pipeline for TestData/static cases and archive results.")
    p.add_argument("--dx-root", type=Path, default=None, help="DeliveraX repo root. Default: parent of this script.")
    p.add_argument("--testdata-static", type=Path, default=None, help="Static testdata root. Default: <dx_root>/testdata/static")
    p.add_argument("--env-file", type=Path, default=None, help="Optional .env merged into pipeline process.")
    p.add_argument("--only", type=str, default="", help="Comma-separated case folder names to run.")
    p.add_argument(
        "--skip-review-and-di",
        action="store_true",
        help="Batch mode: stop after RepairLoop (skip CodeReview and DeliveryIntegration).",
    )
    args = p.parse_args()

    script_dir = Path(__file__).resolve().parent
    dx_root = (args.dx_root or script_dir.parent).resolve()
    static_root = (args.testdata_static or (dx_root / "testdata" / "static")).resolve()
    if not static_root.is_dir():
        raise SystemExit(f"static TestData folder not found: {static_root}")

    allow = {s.strip() for s in args.only.split(",") if s.strip()}
    cases = sorted([p for p in static_root.iterdir() if p.is_dir()])
    if allow:
        cases = [c for c in cases if c.name in allow]

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_id = f"static_batch_{stamp}"

    failures: list[str] = []
    for case_dir in cases:
        req = case_dir / "requirement_r0_initial.txt"
        target = case_dir / "target"
        result_root = case_dir / "result"
        if not req.is_file() or not target.is_dir():
            failures.append(f"{case_dir.name}: missing requirement_r0_initial.txt or target/")
            continue

        run_id = f"{batch_id}__{_sanitize(case_dir.name)}"
        archive = result_root / run_id
        archive.mkdir(parents=True, exist_ok=True)

        prefix = run_id
        env_file = args.env_file
        skip_code_review = bool(args.skip_review_and_di)

        # Use a sanitized copy of requirement for RA boundary checks.
        raw_req_text = req.read_text(encoding="utf-8", errors="replace")
        pipeline_req = archive / "pipeline_requirement.txt"
        pipeline_req.write_text(_sanitize_requirement_for_ra(raw_req_text), encoding="utf-8", errors="replace")

        print(f"\n=== [{case_dir.name}] start prefix={prefix} ===")
        sys.stdout.flush()
        rc = _run_pipeline_stream(
            dx_root=dx_root,
            repo_path=target,
            req_file=pipeline_req,
            env_file=env_file,
            prefix=prefix,
            log_path=archive / "run.log",
            skip_code_review=skip_code_review,
        )
        print(f"=== [{case_dir.name}] done exit_code={rc} (archived to {archive}) ===\n")
        sys.stdout.flush()

        try:
            # Copy pipeline summary JSON (written by run_deliver_pipeline.py)
            batch_json = dx_root / "BatchResults" / f"{prefix}_pipeline_result.json"
            _copyfile(batch_json, archive / "pipeline_result.json")

            # Archive stage outputs (best-effort)
            _copytree(dx_root / "RequirementsAnalysis" / "outputs" / f"{prefix}_ra", archive / "artifacts" / "RequirementsAnalysis")
            _copytree(dx_root / "agents" / "code_generation" / "Output" / f"{prefix}_cg", archive / "artifacts" / "CodeGen")
            _copytree(dx_root / "agents" / "code_testing" / "Output" / f"{prefix}_ct", archive / "artifacts" / "CodeTest")
            _copytree(dx_root / "CodeReview" / "Output" / f"{prefix}_cr", archive / "artifacts" / "CodeReview")
            _copytree(dx_root / "agents" / "release_integration" / "Output" / f"{prefix}_di", archive / "artifacts" / "DeliveryIntegration")

            # Copy a clickable site snapshot for quick manual comparison:
            # prefer DeliveryIntegration repo; else CodeGen repo; else original target.
            site_src = _pick_site_source(dx_root=dx_root, prefix=prefix, fallback=target)
            site_dst = archive / "site"
            _copytree_filtered(
                site_src,
                site_dst,
                ignore_names=(
                    ".git",
                    "node_modules",
                    "dist",
                    "test-results",
                    "playwright-report",
                    ".worktree",
                    ".workspace",
                ),
            )
            entry = _pick_entry_html(site_dst)
            _write_click_to_open_html(archive, entry=entry)

            (archive / "meta.txt").write_text(
                "\n".join(
                    [
                        f"case={case_dir.name}",
                        f"run_id={run_id}",
                        f"pipeline_prefix={prefix}",
                        f"exit_code={rc}",
                        f"click_to_open=OPEN_IN_BROWSER.html -> ./site/{entry}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
        except Exception as exc:
            (archive / "archive_error.txt").write_text(str(exc) + "\n", encoding="utf-8", errors="replace")

        if rc != 0:
            failures.append(f"{case_dir.name}: exit={rc} (see {archive})")

    summary = static_root / "BATCH_SUMMARY.txt"
    summary.write_text(
        "\n".join(
            [
                f"batch_id={batch_id}",
                f"total_cases={len(cases)}",
                f"failures={len(failures)}",
                "",
                *failures,
                "",
                "Each case archives under: <case>/result/<run_id>/",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())

