from __future__ import annotations

"""
Cross-platform full DeliveraX orchestration (CLI).

Order: RequirementsAnalysis → SolutionDesign → CodeGen → RepairLoop
→ CodeReview → (optional) DeliveryIntegration.

DeliveryIntegration runs only when RepairLoop exits success (tests passed),
CodeReview was not skipped, and CodeReview CLI exited 0 — matching
DeliveryIntegration upstream gate (test passed + review approved).
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
import json


def _import_dotenv(path: Path | None) -> None:
    if not path or not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line)
        if m:
            os.environ[m.group(1)] = m.group(2).strip()


def _run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> int:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(cmd, cwd=str(cwd), env=merged).returncode


def _latest_design(dx_root: Path) -> Path:
    out = dx_root / "agents" / "solution_design" / "Output"
    if not out.is_dir():
        raise SystemExit(f"SolutionDesign Output missing: {out}")
    designs = sorted(
        out.glob("technical_design_*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not designs:
        raise SystemExit(f"No technical_design_*.md under {out}")
    return designs[0]


def _sanitize_prefix(s: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", s.strip())
    return cleaned or "pipe"


def main() -> None:
    p = argparse.ArgumentParser(
        description=(
            "Run RA → SD → CodeGen → RepairLoop → CodeReview → DeliveryIntegration "
            "(DI only when tests passed and review approved)."
        )
    )
    p.add_argument(
        "--dx-root",
        type=Path,
        default=None,
        help="DeliveraX repo root (contains agents/, CodeGen, …). "
        "Default: parent of this script's directory.",
    )
    p.add_argument(
        "--repo-path",
        type=Path,
        required=True,
        help="Target application repository root (forward slashes OK).",
    )
    p.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Optional .env (KEY=VALUE) merged into the process environment.",
    )
    p.add_argument(
        "--requirement-file",
        type=Path,
        default=None,
        help="Requirement plain text file. If omitted, uses --requirement-text or built-in default.",
    )
    p.add_argument(
        "--requirement-text",
        type=str,
        default="",
        help="Raw requirement text when --requirement-file is not set.",
    )
    p.add_argument(
        "--pipeline-prefix",
        type=str,
        default="",
        help="Stable id prefix for RA run-id and task ids. Default: pipe_YYYYMMDDhhmmss.",
    )
    p.add_argument(
        "--max-repair-iterations",
        type=int,
        default=5,
        help="RepairLoop --max-iterations.",
    )
    p.add_argument(
        "--skip-code-review",
        action="store_true",
        help="Stop after RepairLoop (no CodeReview / no DeliveryIntegration).",
    )
    p.add_argument(
        "--skip-delivery-integration",
        action="store_true",
        help="Never run DeliveryIntegration (even if tests and review pass).",
    )
    p.add_argument(
        "--mock-llm",
        action="store_true",
        help="RequirementsAnalysis without --use-real-llm (mock spec).",
    )
    p.add_argument(
        "--solution-design-local-only",
        action="store_true",
        help="Pass --local-only to SolutionDesign.",
    )
    p.add_argument(
        "--codegen-local-only",
        action="store_true",
        help="Pass --local-only to CodeGen.",
    )
    p.add_argument(
        "--delivery-no-llm",
        action="store_true",
        help="Pass --no-llm to DeliveryIntegration.",
    )
    p.add_argument(
        "--code-review-max-llm-calls",
        type=int,
        default=28,
        help="CodeReview --max-llm-calls.",
    )
    args = p.parse_args()

    script_dir = Path(__file__).resolve().parent
    dx_root = (args.dx_root or script_dir.parent).resolve()
    repo_path = args.repo_path.resolve()
    if not repo_path.is_dir():
        raise SystemExit(f"repo-path not found: {repo_path}")

    _import_dotenv(args.env_file)
    if not os.environ.get("DEEPSEEK_BASE_URL"):
        os.environ.setdefault("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    # Ensure repo-local packages (e.g. stage_contracts/) are importable for stage entrypoints
    # that are executed with different working directories.
    existing_pythonpath = os.environ.get("PYTHONPATH", "")
    dx_root_str = str(dx_root)
    if existing_pythonpath:
        if dx_root_str not in existing_pythonpath.split(os.pathsep):
            os.environ["PYTHONPATH"] = dx_root_str + os.pathsep + existing_pythonpath
    else:
        os.environ["PYTHONPATH"] = dx_root_str

    prefix = _sanitize_prefix(args.pipeline_prefix or f"pipe_{datetime.now():%Y%m%d%H%M%S}")
    run_id_ra = f"{prefix}_ra"
    task_cg = f"{prefix}_cg"
    task_ct = f"{prefix}_ct"
    task_cr = f"{prefix}_cr"
    task_di = f"{prefix}_di"

    if args.requirement_file:
        req_body = Path(args.requirement_file).read_text(encoding="utf-8")
    elif str(args.requirement_text).strip():
        req_body = str(args.requirement_text)
    else:
        default_txt = script_dir / "default_requirement_cn.txt"
        if not default_txt.is_file():
            raise SystemExit(f"Missing default requirement file: {default_txt}")
        req_body = default_txt.read_text(encoding="utf-8")

    print(f"=== Delivera pipeline === dx_root={dx_root} prefix={prefix} repo={repo_path}")
    pipeline_result: dict[str, object] = {
        "schema_version": "1.0",
        "prefix": prefix,
        "dx_root": str(dx_root),
        "repo_path": str(repo_path),
        "requirement_file": str(args.requirement_file) if args.requirement_file else "",
        "started_at": datetime.now().isoformat(),
        "stages": {},
    }
    stages: dict[str, object] = {}
    pipeline_result["stages"] = stages

    py = sys.executable

    # 1) RequirementsAnalysis
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".txt",
        delete=False,
    ) as tmp:
        tmp.write(req_body)
        tmp_path = Path(tmp.name)
    try:
        ra_cmd = [
            py,
            "run.py",
            "--output-dir",
            "outputs",
            "--run-id",
            run_id_ra,
            "--input-file",
            str(tmp_path),
        ]
        if not args.mock_llm:
            ra_cmd.append("--use-real-llm")
        rc = _run(ra_cmd, cwd=dx_root / "agents" / "requirement_analysis")
        stages["RequirementsAnalysis"] = {"exit_code": rc}
        if rc != 0:
            raise SystemExit(f"RequirementsAnalysis failed (exit {rc})")
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass

    prd = dx_root / "agents" / "requirement_analysis" / "outputs" / run_id_ra / "requirement_prd.md"
    spec = dx_root / "agents" / "requirement_analysis" / "outputs" / run_id_ra / "requirement_spec.json"
    if not prd.is_file():
        raise SystemExit(f"Missing PRD (RA may have rejected input): {prd}")

    # 2) SolutionDesign
    sd_cmd = [
        py,
        "run.py",
        "--requirement",
        str(prd),
        "--repo-path",
        str(repo_path),
        "--task-id",
        task_cg,
        "--max-context-files",
        "32",
    ]
    if args.solution_design_local_only:
        sd_cmd.append("--local-only")
    rc = _run(sd_cmd, cwd=dx_root / "agents" / "solution_design")
    stages["SolutionDesign"] = {"exit_code": rc}
    if rc != 0:
        raise SystemExit(f"SolutionDesign failed (exit {rc})")

    design_path = _latest_design(dx_root)
    print(f"DESIGN={design_path}")

    # 3) CodeGen
    ws = dx_root / "agents" / "solution_design" / ".workspace"
    cg_cmd = [
        py,
        "run.py",
        "--design",
        str(design_path),
        "--repo-path",
        str(repo_path),
        "--task-id",
        task_cg,
        "--workspace-dir",
        str(ws),
    ]
    if args.codegen_local_only:
        cg_cmd.append("--local-only")
    rc = _run(cg_cmd, cwd=dx_root / "agents" / "code_generation")
    stages["CodeGen"] = {"exit_code": rc}
    if rc != 0:
        raise SystemExit(f"CodeGen failed (exit {rc})")

    codegen_json = dx_root / "agents" / "code_generation" / "Output" / task_cg / "codegen_result.json"
    if not codegen_json.is_file():
        raise SystemExit(f"Missing CodeGen result: {codegen_json}")

    # 4) RepairLoop
    repo_forward = repo_path.as_posix()
    rl_cmd = [
        py,
        "run.py",
        "--dx-root",
        str(dx_root),
        "--max-iterations",
        str(max(1, int(args.max_repair_iterations))),
        "--codegen-task-id",
        task_cg,
        "--codetest-task-id",
        task_ct,
        "--design",
        str(design_path),
        "--repo-path",
        repo_forward,
        "--workspace-dir",
        str(ws),
        "--requirement-path",
        str(spec),
        "--initial-codegen-result",
        str(codegen_json),
    ]
    repair_exit = _run(rl_cmd, cwd=dx_root / "agents" / "repair_loop")
    print(f"RepairLoop exit code: {repair_exit}")
    stages["RepairLoop"] = {"exit_code": repair_exit}

    codetest_json = dx_root / "agents" / "code_testing" / "Output" / task_ct / "code_test_result.json"
    cr_exit = 0
    di_exit: int | None = None

    # 5) CodeReview
    if not args.skip_code_review:
        if not codetest_json.is_file():
            raise SystemExit(f"Missing CodeTest result after RepairLoop: {codetest_json}")
        diff_path = dx_root / "agents" / "code_generation" / "Output" / task_cg / "code_changes.diff"
        cr_cmd = [
            py,
            "run.py",
            "--test-result",
            str(codetest_json),
            "--design",
            str(design_path),
            "--diff",
            str(diff_path),
            "--codegen-result",
            str(codegen_json),
            "--requirement",
            str(spec),
            "--task-id",
            task_cr,
            "--max-llm-calls",
            str(int(args.code_review_max_llm_calls)),
        ]
        cr_exit = _run(cr_cmd, cwd=dx_root / "agents" / "code_review")
        print(f"CodeReview exit code: {cr_exit}")
        stages["CodeReview"] = {"exit_code": cr_exit}
    else:
        print("Skipped CodeReview (--skip-code-review).")
        stages["CodeReview"] = {"skipped": True}

    # 6) DeliveryIntegration
    if not args.skip_delivery_integration:
        if args.skip_code_review:
            print("Skipping DeliveryIntegration: CodeReview was skipped (upstream gate needs review).")
        elif repair_exit != 0:
            print("Skipping DeliveryIntegration: RepairLoop did not pass tests.")
        elif cr_exit != 0:
            print("Skipping DeliveryIntegration: CodeReview did not exit successfully.")
        else:
            review_json = dx_root / "agents" / "code_review" / "Output" / task_cr / "code_review_result.json"
            if not review_json.is_file():
                raise SystemExit(f"Missing CodeReview result: {review_json}")
            di_cmd = [
                py,
                "run.py",
                "--codegen-result",
                str(codegen_json),
                "--test-result",
                str(codetest_json),
                "--review-result",
                str(review_json),
                "--task-id",
                task_di,
                "--force",
            ]
            if args.delivery_no_llm:
                di_cmd.append("--no-llm")
            di_exit = _run(di_cmd, cwd=dx_root / "agents" / "release_integration")
            print(f"DeliveryIntegration exit code: {di_exit}")
            stages["DeliveryIntegration"] = {"exit_code": di_exit}
    else:
        print("Skipped DeliveryIntegration (--skip-delivery-integration).")
        stages["DeliveryIntegration"] = {"skipped": True}

    print("--- Summary ---")
    print(f"RA outputs: {dx_root / 'RequirementsAnalysis' / 'outputs' / run_id_ra}")
    print(f"Design: {design_path}")
    print(f"CodeGen: {codegen_json}")
    print(f"RepairLoop summary: {dx_root / 'CodeTest' / 'Output' / task_ct / 'pipeline_loop_summary.json'}")
    print(f"CodeTest result: {codetest_json}")
    if not args.skip_code_review:
        print(f"CodeReview: {dx_root / 'CodeReview' / 'Output' / task_cr / 'code_review_result.json'}")
    if di_exit is not None:
        print(f"DeliveryIntegration: {dx_root / 'DeliveryIntegration' / 'Output' / task_di}")

    exit_code = 0
    if repair_exit != 0:
        exit_code = max(exit_code, repair_exit)
    if not args.skip_code_review and cr_exit != 0:
        exit_code = max(exit_code, cr_exit)
    if di_exit is not None and di_exit != 0:
        exit_code = max(exit_code, di_exit)
    pipeline_result["ended_at"] = datetime.now().isoformat()
    pipeline_result["exit_code"] = exit_code
    try:
        out_path = dx_root / "BatchResults" / f"{prefix}_pipeline_result.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(pipeline_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Pipeline result written: {out_path}")
    except OSError:
        pass
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
