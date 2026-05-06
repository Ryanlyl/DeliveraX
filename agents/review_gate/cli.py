from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .runner import outcome_exit_code, run_codereview


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="CodeReview: diff + design + code_test_result → code_review_result.json"
    )
    p.add_argument("--codegen-result", help="Optional CodeGen codegen_result.json (fills missing paths).")
    p.add_argument("--design", help="Technical design Markdown path.")
    p.add_argument("--diff", help="Unified diff file (e.g. code_changes.diff).")
    p.add_argument("--test-result", required=True, help="Path to code_test_result.json (required).")
    p.add_argument("--requirement", default="", help="Optional requirement_spec.json path.")
    p.add_argument("--task-id", default="", help="Task id; fallback: codegen_result or code_test_result.")
    p.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parents[1] / "Output"),
        help="Root for CodeReview/Output/<task-id>/",
    )
    p.add_argument("--policy-pack", default="", help="Optional Markdown with extra team conventions.")
    p.add_argument("--local-only", action="store_true", help="Skip LLM; smoke status 'test'.")
    p.add_argument("--max-llm-calls", type=int, default=None, help="Override CODEREVIEW_LLM_MAX_CALLS budget.")
    return p


def main() -> None:
    args = build_parser().parse_args()
    cg = str(args.codegen_result or "").strip() or None
    design = str(args.design or "").strip() or None
    diff_p = str(args.diff or "").strip() or None
    req = str(args.requirement or "").strip() or None
    pp = str(args.policy_pack or "").strip() or None
    task = str(args.task_id or "").strip() or None

    try:
        result = run_codereview(
            codegen_result_path=cg,
            design_path_cli=design,
            diff_path_cli=diff_p,
            test_result_path=str(Path(args.test_result).resolve()),
            requirement_path_cli=req,
            task_id_cli=task,
            output_dir=args.output_dir,
            policy_pack_path=pp,
            local_only=bool(args.local_only),
            max_llm_calls_override=args.max_llm_calls,
        )
    except KeyboardInterrupt:
        raise SystemExit("CodeReview interrupted.") from None
    except RuntimeError as exc:
        raise SystemExit(f"CodeReview failed: {exc}") from exc

    rp = str(result.get("result_json_path") or "")
    print(f"CodeReview result: {rp}")
    print(f"status={result.get('status')} merge_recommendation={result.get('merge_recommendation')}")
    print(result.get("summary", ""))

    if bool(result.get("local_only")):
        sys.exit(0)
    sys.exit(outcome_exit_code(result))


if __name__ == "__main__":
    main()
