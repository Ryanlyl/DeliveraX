from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate repository code changes from a SolutionDesign technical design Markdown."
    )
    parser.add_argument(
        "--design",
        required=True,
        help="Path to SolutionDesign/Output/technical_design_*.md.",
    )
    parser.add_argument(
        "--repo-path",
        help="Optional explicit repository path. Overrides implementation_contract.repo_root workspace resolution.",
    )
    parser.add_argument(
        "--workspace-dir",
        default=str(Path(__file__).resolve().parents[2] / "SolutionDesign" / ".workspace"),
        help="Existing workspace that contains fetched repositories. Defaults to SolutionDesign/.workspace.",
    )
    parser.add_argument(
        "--task-id",
        help="Optional SolutionDesign task id if the repository lives in a task-level workspace.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parents[1] / "Output"),
        help="Directory for generated .diff and report artifacts.",
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Run parsing, workspace resolution, diff generation, and report output without LLM code edits.",
    )
    parser.add_argument(
        "--max-context-files",
        type=int,
        default=32,
        help="Maximum number of repository files to include in model context.",
    )
    parser.add_argument(
        "--max-file-chars",
        type=int,
        default=24000,
        help="Maximum characters to include from each context file.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        from .graph import run_codegen
    except ModuleNotFoundError as exc:
        missing = exc.name or "required dependency"
        raise SystemExit(
            f"Missing dependency `{missing}`. Install with: python -m pip install -r CodeGen/requirements.txt"
        ) from exc

    try:
        result = run_codegen(
            design_path=args.design,
            repo_path=args.repo_path,
            workspace_dir=args.workspace_dir,
            task_id=args.task_id,
            output_dir=args.output_dir,
            local_only=args.local_only,
            max_context_files=args.max_context_files,
            max_file_chars=args.max_file_chars,
        )
    except KeyboardInterrupt:
        raise SystemExit("CodeGen interrupted by user.") from None
    except RuntimeError as exc:
        raise SystemExit(f"CodeGen failed: {exc}") from None
    print(f"Code diff generated: {result['diff_path']}")
    print(f"CodeGen report generated: {result['report_path']}")
    print(f"CodeGen result generated: {result['result_json_path']}")
