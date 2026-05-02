from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .models import RequirementAnalysisResult


@dataclass
class LocalDebugArtifacts:
    run_dir: Path
    input_path: Path
    spec_path: Path | None
    markdown_path: Path | None
    report_path: Path


def build_run_dir(output_dir: Path, run_id: str | None = None) -> Path:
    if run_id:
        dir_name = run_id
    else:
        dir_name = datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S")
    run_dir = output_dir / dir_name
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def write_local_debug_artifacts(
    output_dir: Path,
    user_input: str,
    result: RequirementAnalysisResult,
    run_id: str | None = None,
) -> LocalDebugArtifacts:
    run_dir = build_run_dir(output_dir, run_id=run_id)

    input_path = run_dir / "input.txt"
    input_path.write_text(user_input, encoding="utf-8")

    spec_path: Path | None = None
    if result.spec is not None:
        spec_path = run_dir / "requirement_spec.json"
        spec_path.write_text(
            json.dumps(result.spec.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    markdown_path: Path | None = None
    if result.markdown is not None:
        markdown_path = run_dir / "requirement_prd.md"
        markdown_path.write_text(result.markdown, encoding="utf-8")

    report_path = run_dir / "report.json"
    report_path.write_text(
        json.dumps(result.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return LocalDebugArtifacts(
        run_dir=run_dir,
        input_path=input_path,
        spec_path=spec_path,
        markdown_path=markdown_path,
        report_path=report_path,
    )
