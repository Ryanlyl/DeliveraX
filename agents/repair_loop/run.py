from __future__ import annotations

"""
Automated repair loop: CodeTest -> FeedbackTriage -> (optional) CodeGen or CodeTest with repair feedback -> repeat.

Stops when CodeTest passes, when triage routes to an owner without auto-repair,
or after max_iterations CodeTest executions. Writes pipeline_loop_summary.json next to code_test_result.json.
"""

import argparse
import json
import sys
from pathlib import Path
from subprocess import CalledProcessError, run


def _norm_passed(status: str) -> bool:
    return str(status or "").strip().lower() in {"passed", "pass", "ok", "success"}


def main() -> None:
    p = argparse.ArgumentParser(description="Repair loop: CodeTest + triage (+ CodeGen retry on product_code).")
    p.add_argument(
        "--dx-root",
        type=str,
        default=str(Path(__file__).resolve().parents[1]),
        help="DeliveraX-main root containing CodeGen/CodeTest/FeedbackTriage",
    )
    p.add_argument(
        "--max-iterations",
        type=int,
        default=5,
        help="Maximum number of CodeTest executions before stopping.",
    )
    p.add_argument(
        "--codegen-task-id",
        required=True,
        help="Stable task id passed to CodeGen --task-id (output under CodeGen/Output/<id>/codegen_result.json).",
    )
    p.add_argument(
        "--codetest-task-id",
        required=True,
        help="Stable task id passed to CodeTest --task-id.",
    )
    p.add_argument(
        "--design",
        required=True,
        help="Path to SolutionDesign technical_design_*.md (for CodeGen repair steps).",
    )
    p.add_argument(
        "--repo-path",
        required=True,
        help="Explicit repo root for CodeGen (--repo-path), use forward slashes on Windows.",
    )
    p.add_argument(
        "--workspace-dir",
        default="",
        help="SolutionDesign workspace dir for CodeGen. Default: <dx-root>/SolutionDesign/.workspace",
    )
    p.add_argument(
        "--requirement-path",
        required=True,
        help="Path to requirement_spec.json for CodeTest --requirement",
    )
    p.add_argument(
        "--initial-codegen-result",
        required=True,
        help="Starting CodeGen/Output/<...>/codegen_result.json path for iteration 1.",
    )
    args = p.parse_args()
    dx_root = Path(args.dx_root).resolve()

    codegen_root = dx_root / "agents" / "code_generation"
    codetest_root = dx_root / "agents" / "code_testing"
    ft_run = dx_root / "agents" / "feedback_triage" / "run.py"

    ws = (
        Path(args.workspace_dir).resolve()
        if str(args.workspace_dir).strip()
        else (dx_root / "SolutionDesign" / ".workspace").resolve()
    )

    codegen_result = Path(args.initial_codegen_result).resolve()

    codetest_task_id = args.codetest_task_id
    codegen_task_id = args.codegen_task_id

    std_codegen_result = (dx_root / "agents" / "code_generation" / "Output" / codegen_task_id / "codegen_result.json").resolve()

    summary: dict[str, object] = {
        "schema_version": "1.0",
        "codetest_task_id": codetest_task_id,
        "codegen_task_id": codegen_task_id,
        "iterations": [],
        "final_outcome": "",
        "stop_reason": "",
    }

    sys.path.insert(0, str(dx_root / "agents" / "feedback_triage"))
    from triage import run_triage  # noqa: PLC0415

    if not codegen_result.is_file():
        raise SystemExit(f"codegen_result not found: {codegen_result}")
    if (
        not (codegen_root / "run.py").is_file()
        or not (codetest_root / "run.py").is_file()
        or not ft_run.is_file()
    ):
        raise SystemExit("CodeGen/CodeTest/FeedbackTriage entry scripts missing under dx-root.")

    codetest_out_base = dx_root / "agents" / "code_testing" / "Output"

    max_iter = max(1, int(args.max_iterations))
    outcome = "failed"
    stop_reason = ""
    codetest_extra_args: list[str] = []
    env_retry_used = False

    for ct_round in range(max_iter):
        # Always refresh task copy: stale workspace breaks round 1 after a prior aborted run.
        force = True
        ct_cmd = [
            sys.executable,
            "run.py",
            "--codegen-result",
            str(codegen_result),
            "--requirement",
            str(Path(args.requirement_path).resolve()),
            "--task-id",
            codetest_task_id,
            "--workspace-dir",
            str(codetest_root / ".workspace"),
            "--max-llm-calls",
            "32",
        ]
        if force:
            ct_cmd.append("--force")
        ct_cmd.extend(codetest_extra_args)
        completed = run(ct_cmd, cwd=str(codetest_root))

        result_path = codetest_out_base / codetest_task_id / "code_test_result.json"
        if completed.returncode not in {0, 2}:
            outcome = "failed"
            stop_reason = f"code_test_fatal_exit:{completed.returncode} at round_{ct_round + 1}"
            break

        if not result_path.is_file():
            outcome = "failed"
            stop_reason = (
                f"code_test_result.json missing after CodeTest subprocess "
                f"(exit {completed.returncode})"
            )
            break

        ct_payload = json.loads(result_path.read_text(encoding="utf-8"))

        triage_payload = run_triage(result_path=result_path)

        iteration_record = {
            "round": ct_round + 1,
            "codetest_status": ct_payload.get("status"),
            "triage_failure_category": triage_payload.get("failure_category"),
            "triage_owner": triage_payload.get("recommended_owner"),
            "triage_action": triage_payload.get("recommended_action"),
            "result_json_path": str(result_path),
            "feedback_paths": sorted(
                p.name for p in result_path.parent.glob("feedback*.md") if p.is_file()
            ),
        }
        lst = summary.get("iterations")
        assert isinstance(lst, list)
        lst.append(iteration_record)

        if _norm_passed(str(ct_payload.get("status"))):
            outcome = "passed"
            stop_reason = "code_test_passed"
            summary["pipeline_loop_summary_path"] = str(
                codetest_out_base / codetest_task_id / "pipeline_loop_summary.json"
            )
            break

        if ct_round >= max_iter - 1:
            outcome = "failed"
            stop_reason = (
                "max_iterations_exhausted: increase --max-iterations or manually fix upstream"
            )
            break

        owner = str(triage_payload.get("recommended_owner") or "")
        fb_md = result_path.parent / "feedback_to_codegen.md"
        category = str(triage_payload.get("failure_category") or "")

        if owner == "environment" and category == "environment":
            if env_retry_used:
                outcome = "failed"
                stop_reason = "environment_auto_fix_exhausted"
                break
            env_retry_used = True
            assert isinstance(lst, list) and lst
            cast_last = lst[-1]
            if isinstance(cast_last, dict):
                cast_last["environment_retry_scheduled"] = True
            # Rerun CodeTest once; CodeTest preflight should attempt best-effort environment stabilization.
            codetest_extra_args = []
            continue

        if owner == "codegen" and category == "product_code":
            if not fb_md.is_file():
                outcome = "failed"
                stop_reason = "feedback_to_codegen.md missing — run FeedbackTriage or check triage routing"
                break
            try:
                run(
                    [
                        sys.executable,
                        "run.py",
                        "--design",
                        str(Path(args.design).resolve()),
                        "--repo-path",
                        args.repo_path,
                        "--workspace-dir",
                        str(ws),
                        "--task-id",
                        codegen_task_id,
                        "--repair-feedback",
                        str(fb_md),
                    ],
                    cwd=str(codegen_root),
                    check=True,
                )
            except CalledProcessError as exc:
                outcome = "failed"
                stop_reason = f"codegen_repair_failed: {exc}"
                break

            codegen_result = std_codegen_result
            codetest_extra_args = []
            continue

        if owner == "codetest" and category == "test_design":
            fb_ct = result_path.parent / "feedback_to_codetest.md"
            if not fb_ct.is_file():
                outcome = "failed"
                stop_reason = "feedback_to_codetest.md missing — run FeedbackTriage or check triage routing"
                break
            codetest_extra_args = ["--repair-feedback", str(fb_ct.resolve())]
            assert isinstance(lst, list) and lst
            cast_last = lst[-1]
            if isinstance(cast_last, dict):
                cast_last["codetest_repair_scheduled"] = True
            continue

        outcome = "failed"
        stop_reason = (
            f"no_auto_repair_for_owner:{owner or 'unknown'}_category:{category or 'unknown'}"
        )
        break

    summary["final_outcome"] = outcome
    summary["stop_reason"] = stop_reason
    _write_summary(dx_root, codetest_task_id, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    raise SystemExit(0 if outcome == "passed" else 2)


def _write_summary(dx_root: Path, codetest_task_id: str, summary: dict[str, object]) -> None:
    out = dx_root / "agents" / "code_testing" / "Output" / codetest_task_id / "pipeline_loop_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
