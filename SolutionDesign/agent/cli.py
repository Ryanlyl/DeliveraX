from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a technical solution design from a structured PRD and repository context."
    )
    parser.add_argument(
        "--requirement",
        required=True,
        help="Path to the structured requirement Markdown file.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--repo-url", help="Public GitHub repository URL to clone or download.")
    source.add_argument("--repo-path", help="Path to an already available local repository.")
    parser.add_argument("--repo-ref", help="Branch, tag, or commit SHA. Defaults to repository default branch.")
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parents[1] / "Output"),
        help="Directory for generated technical design Markdown.",
    )
    parser.add_argument(
        "--template",
        default=str(Path(__file__).resolve().parents[1] / "templates" / "technical_design_template.md"),
        help="Path to technical design template Markdown.",
    )
    parser.add_argument(
        "--workspace-dir",
        help="Runtime workspace for cloned repositories. Overrides SOLUTION_DESIGN_WORKSPACE_DIR.",
    )
    parser.add_argument(
        "--task-id",
        help="Optional task id for task-level repository workspace isolation.",
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Run without LLM calls and generate a heuristic draft. Useful for smoke tests.",
    )
    parser.add_argument(
        "--max-context-files",
        type=int,
        default=24,
        help="Maximum number of repository files to include in model context.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        from .graph import run_solution_design
    except ModuleNotFoundError as exc:
        missing = exc.name or "required dependency"
        raise SystemExit(
            f"Missing dependency `{missing}`. Install with: python -m pip install -r SolutionDesign/requirements.txt"
        ) from exc

    result = run_solution_design(
        requirement_path=args.requirement,
        repo_url=args.repo_url,
        repo_path=args.repo_path,
        repo_ref=args.repo_ref,
        output_dir=args.output_dir,
        template_path=args.template,
        workspace_dir=args.workspace_dir,
        task_id=args.task_id,
        local_only=args.local_only,
        max_context_files=args.max_context_files,
    )
    print(f"Solution design generated: {result['output_path']}")
