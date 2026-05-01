from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Integrate a tested and reviewed CodeGen diff into the matching "
            "SolutionDesign workspace repository."
        )
    )
    parser.add_argument(
        "--codegen-result",
        help="Path to CodeGen/Output/<task-id>/codegen_result.json.",
    )
    parser.add_argument(
        "--changeset",
        help="Optional delivery changeset JSON. Can point at a codegen_result_path.",
    )
    parser.add_argument(
        "--test-result",
        help="Optional upstream code test result JSON. The status must be passed/success.",
    )
    parser.add_argument(
        "--review-result",
        help="Optional upstream code review result JSON. The status must be approved.",
    )
    parser.add_argument(
        "--test-status",
        help="Explicit upstream code test status. Defaults to assumed passed when no result is provided.",
    )
    parser.add_argument(
        "--review-status",
        help="Explicit upstream code review status. Defaults to assumed approved when no result is provided.",
    )
    parser.add_argument(
        "--task-id",
        help="Delivery integration task id. Defaults to delivery-<codegen-task-id>.",
    )
    parser.add_argument(
        "--workspace-dir",
        default=str(Path(__file__).resolve().parents[1] / ".workspace"),
        help="DeliveryIntegration runtime workspace. Defaults to DeliveryIntegration/.workspace.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parents[1] / "Output"),
        help="Directory for final diff, summary, PR body, and result JSON.",
    )
    parser.add_argument(
        "--integration-branch",
        help="Local integration branch name. Defaults to delivery/<task-id>.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing DeliveryIntegration task workspace for the same task id.",
    )
    parser.add_argument(
        "--no-commit",
        action="store_true",
        help="Leave applied changes uncommitted in the integration worktree.",
    )
    parser.add_argument(
        "--allow-source-head-drift",
        action="store_true",
        help="Allow source workspace HEAD to differ from CodeGen source_commit_sha.",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable LLM summary generation and use deterministic summary templates.",
    )
    parser.add_argument(
        "--require-llm",
        action="store_true",
        help="Fail the run if LLM summary generation is unavailable or fails.",
    )
    parser.add_argument(
        "--summary-max-diff-chars",
        type=int,
        default=24000,
        help="Maximum final diff characters to send to the LLM summary step.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not args.codegen_result and not args.changeset:
        raise SystemExit("Provide --codegen-result or --changeset.")
    if args.no_llm and args.require_llm:
        raise SystemExit("Use either --no-llm or --require-llm, not both.")

    try:
        from .graph import run_delivery_integration
    except ModuleNotFoundError as exc:
        missing = exc.name or "required dependency"
        raise SystemExit(
            "Missing dependency "
            f"`{missing}`. Install with: python -m pip install -r DeliveryIntegration/requirements.txt"
        ) from exc

    try:
        result = run_delivery_integration(
            codegen_result_path=args.codegen_result,
            changeset_path=args.changeset,
            test_result_path=args.test_result,
            review_result_path=args.review_result,
            test_status=args.test_status,
            review_status=args.review_status,
            task_id=args.task_id,
            workspace_dir=args.workspace_dir,
            output_dir=args.output_dir,
            integration_branch=args.integration_branch,
            force=args.force,
            create_commit=not args.no_commit,
            allow_source_head_drift=args.allow_source_head_drift,
            use_llm=not args.no_llm,
            require_llm=args.require_llm,
            summary_max_diff_chars=args.summary_max_diff_chars,
        )
    except KeyboardInterrupt:
        raise SystemExit("DeliveryIntegration interrupted by user.") from None
    except RuntimeError as exc:
        raise SystemExit(f"DeliveryIntegration failed: {exc}") from None

    print(f"Integration repo: {result['integration_repo_path']}")
    print(f"Final diff generated: {result['final_diff_path']}")
    print(f"Change summary generated: {result['summary_path']}")
    print(f"PR body generated: {result['pr_body_path']}")
    print(f"DeliveryIntegration result generated: {result['result_json_path']}")
