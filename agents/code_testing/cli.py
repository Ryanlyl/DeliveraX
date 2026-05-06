from __future__ import annotations

import argparse
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="CodeTest: plan, generate, and run frontend tests from CodeGen outputs."
    )
    p.add_argument(
        "--codegen-result",
        help="Path to CodeGen/Output/<task-id>/codegen_result.json",
    )
    p.add_argument("--design", help="Path to technical design Markdown (optional if in codegen result).")
    p.add_argument("--diff", help="Path to code_changes.diff (optional if in codegen result).")
    p.add_argument("--repo-path", help="Path to codegen task repository (optional if in codegen result).")
    p.add_argument("--requirement", help="Optional path to requirement_spec.json.")
    p.add_argument("--task-id", help="Override task id from codegen_result.")
    p.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parents[1] / "Output"),
        help="Output directory root (default CodeTest/Output).",
    )
    p.add_argument(
        "--workspace-dir",
        default=str(Path(__file__).resolve().parents[1] / ".workspace"),
        help="Runtime workspace (task repo copies).",
    )
    p.add_argument(
        "--local-only",
        action="store_true",
        help="Smoke: copy workspace only; no LLM / no npm test. Result status 'test'.",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Replace existing task workspace directory.",
    )
    p.add_argument(
        "--max-llm-calls",
        type=int,
        default=None,
        help="Override CODETEST_LLM_MAX_CALLS_PER_RUN (default 12).",
    )
    p.add_argument(
        "--repair-feedback",
        dest="repair_feedback",
        default="",
        help="Markdown with failed run context (e.g. FeedbackTriage feedback_to_codetest.md); appended to LLM prompts.",
    )
    return p


def main() -> None:
    args = build_parser().parse_args()
    if not args.codegen_result:
        raise SystemExit("Provide --codegen-result pointing to codegen_result.json.")

    try:
        from .graph import run_codetest
    except ModuleNotFoundError as exc:
        missing = exc.name or "required dependency"
        raise SystemExit(
            f"Missing dependency `{missing}`. Install: python -m pip install -r CodeTest/requirements.txt"
        ) from exc

    try:
        rf = str(args.repair_feedback or "").strip()
        result = run_codetest(
            codegen_result_path=args.codegen_result,
            design_path=args.design,
            diff_path=args.diff,
            repo_path=args.repo_path,
            requirement_path=args.requirement,
            task_id=args.task_id,
            output_dir=args.output_dir,
            workspace_dir=args.workspace_dir,
            local_only=args.local_only,
            force=args.force,
            max_llm_calls=args.max_llm_calls,
            repair_feedback_path=rf if rf else None,
        )
    except KeyboardInterrupt:
        raise SystemExit("CodeTest interrupted by user.") from None
    except RuntimeError as exc:
        raise SystemExit(f"CodeTest failed: {exc}") from None

    print(f"CodeTest result: {result.get('result_json_path', '')}")
    print(f"Status: {result.get('status', '')}")
    print(result.get("summary", ""))

    raw_status = str(result.get("status", "")).strip().lower()
    if raw_status in {"passed", "pass", "ok", "success"}:
        return
    local_only = bool(result.get("local_only"))
    if local_only:
        sys.exit(0)
    sys.exit(2)


if __name__ == "__main__":
    main()
