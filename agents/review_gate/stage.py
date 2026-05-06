from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from stage_contracts import (
    ArtifactRef,
    StageRunRequest,
    StageRunResult,
    resolve_stage_artifact_dir,
    write_stage_artifacts,
)


INPUT_PRIORITY = (
    "code_changes",
    "codegen_result",
    "codegen_report",
    "code_test_result",
    "code_test_report",
    "technical_design",
    "requirement_prd",
    "requirement_spec",
)

FAILED_TEST_STATUSES = {
    "failed",
    "fail",
    "failure",
    "error",
    "errored",
    "blocked",
}
PASSED_TEST_STATUSES = {
    "passed",
    "pass",
    "ok",
    "success",
    "succeeded",
}


def run_stage(request: StageRunRequest) -> StageRunResult:
    started_at = datetime.now(timezone.utc)
    logs = ["ReviewGate deterministic stage started"]
    try:
        stage_dir = resolve_stage_artifact_dir(request)
        stage_dir.mkdir(parents=True, exist_ok=True)

        selected = _selected_artifacts(request)
        diff_text, diff_source = _load_diff(request, selected)
        test_payload, test_text, test_source = _load_test_result(request, selected)
        test_status = _infer_test_status(test_payload, test_text)
        diff_stats = _diff_stats(diff_text)
        verdict = _verdict(test_status, diff_stats)
        risks = _risks(verdict, test_status, diff_stats)
        checklist = _checklist(test_status, diff_stats, selected)
        requires_human_approval = _requires_human_approval(request.options)

        review_result = {
            "verdict": verdict,
            "summary": _summary(verdict, test_status, diff_stats),
            "risks": risks,
            "checklist": checklist,
            "upstream_artifacts": [
                artifact.model_dump(mode="json") for artifact in _ordered_upstream_artifacts(selected)
            ],
            "test_status": test_status,
            "diff_stats": diff_stats,
            "requires_human_approval": requires_human_approval,
            "diff_source": str(diff_source) if diff_source else None,
            "test_source": str(test_source) if test_source else None,
        }

        report = _render_report(review_result)
        report_path = stage_dir / "review_report.md"
        result_path = stage_dir / "review_result.json"
        feedback_path = stage_dir / "feedback_review.md"

        report_path.write_text(report.rstrip() + "\n", encoding="utf-8")
        feedback_path.write_text(report.rstrip() + "\n", encoding="utf-8")
        result_path.write_text(
            json.dumps(review_result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        output_artifacts = [
            ArtifactRef(name="review_report", type="markdown", path=str(report_path), role="display"),
            ArtifactRef(name="review_result", type="json", path=str(result_path), role="machine"),
            ArtifactRef(name="feedback_review", type="markdown", path=str(feedback_path), role="handoff"),
        ]
        ended_at = datetime.now(timezone.utc)
        status = "pending_approval" if requires_human_approval else "succeeded"
        result = StageRunResult(
            pipeline_id=request.pipeline_id,
            stage_id=request.stage_id,
            run_id=request.run_id,
            status=status,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=max(0, int((ended_at - started_at).total_seconds() * 1000)),
            input_artifacts=request.input_artifacts,
            output_artifacts=output_artifacts,
            human_output=report,
            data={
                **review_result,
                "review_status": verdict,
                "merge_recommendation": _merge_recommendation(verdict),
            },
            logs=[
                *logs,
                f"ReviewGate verdict: {verdict}",
                f"ReviewGate test status: {test_status}",
            ],
        )
        return write_stage_artifacts(
            request=request,
            result=result,
            input_payload={
                "selected_artifacts": {
                    name: artifact.model_dump(mode="json")
                    for name, artifact in selected.items()
                },
                "options": request.options,
            },
        )
    except Exception as exc:
        result = StageRunResult.from_exception(request=request, started_at=started_at, exc=exc, logs=logs)
        return write_stage_artifacts(request=request, result=result)


def _selected_artifacts(request: StageRunRequest) -> dict[str, ArtifactRef]:
    selected: dict[str, ArtifactRef] = {}
    for name in INPUT_PRIORITY:
        artifact = _first_artifact(request, name)
        if artifact is not None:
            selected[name] = artifact
    return selected


def _first_artifact(request: StageRunRequest, name: str) -> ArtifactRef | None:
    for artifact in request.input_artifacts:
        if artifact.name == name:
            return artifact
    return None


def _ordered_upstream_artifacts(selected: dict[str, ArtifactRef]) -> list[ArtifactRef]:
    return [selected[name] for name in INPUT_PRIORITY if name in selected]


def _load_diff(
    request: StageRunRequest,
    selected: dict[str, ArtifactRef],
) -> tuple[str, Path | None]:
    explicit = request.options.get("diff_path")
    if explicit:
        path = Path(str(explicit))
        return _read_text(path), path

    artifact = selected.get("code_changes")
    if artifact is not None:
        path = Path(artifact.path)
        return _read_text(path), path

    codegen_result = _load_json_artifact(selected.get("codegen_result"))
    for key in ("diff_path", "patch_path", "code_changes_path"):
        raw_path = codegen_result.get(key)
        if raw_path:
            path = Path(str(raw_path))
            return _read_text(path), path
    for key in ("diff", "patch", "changes"):
        value = codegen_result.get(key)
        if isinstance(value, str):
            return value, None

    report = selected.get("codegen_report")
    if report is not None:
        path = Path(report.path)
        return _read_text(path), path
    return "", None


def _load_test_result(
    request: StageRunRequest,
    selected: dict[str, ArtifactRef],
) -> tuple[dict[str, Any], str, Path | None]:
    explicit = request.options.get("test_result_path")
    if explicit:
        path = Path(str(explicit))
        text = _read_text(path)
        return _parse_json(text), text, path

    artifact = selected.get("code_test_result")
    if artifact is not None:
        path = Path(artifact.path)
        text = _read_text(path)
        return _parse_json(text), text, path

    report = selected.get("code_test_report")
    if report is not None:
        path = Path(report.path)
        text = _read_text(path)
        return {}, text, path
    return {}, "", None


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _load_json_artifact(artifact: ArtifactRef | None) -> dict[str, Any]:
    if artifact is None:
        return {}
    return _parse_json(_read_text(Path(artifact.path)))


def _parse_json(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _infer_test_status(payload: dict[str, Any], text: str) -> str:
    candidates = [
        payload.get("status"),
        payload.get("test_status"),
        payload.get("legacy_status"),
        payload.get("result"),
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        normalized = str(candidate).strip().lower()
        if normalized in FAILED_TEST_STATUSES:
            return "failed"
        if normalized in PASSED_TEST_STATUSES:
            return "passed"

    errors = payload.get("errors")
    if isinstance(errors, list) and errors:
        return "failed"

    lowered = text.lower()
    if any(token in lowered for token in ("failed", "failure", "traceback", "assertionerror")):
        return "failed"
    if any(token in lowered for token in ("passed", "success", "succeeded")):
        return "passed"
    return "unknown"


def _diff_stats(diff_text: str) -> dict[str, Any]:
    added = 0
    deleted = 0
    files: set[str] = set()
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                files.add(parts[3].removeprefix("b/"))
            continue
        if line.startswith("+++ ") or line.startswith("--- "):
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            deleted += 1

    has_changes = bool(diff_text.strip()) and (added > 0 or deleted > 0 or bool(files))
    return {
        "files_changed": len(files) if files else (1 if added or deleted else 0),
        "lines_added": added,
        "lines_deleted": deleted,
        "has_changes": has_changes,
    }


def _verdict(test_status: str, diff_stats: dict[str, Any]) -> str:
    if test_status == "failed":
        return "needs_changes"
    if not diff_stats.get("has_changes"):
        return "no_changes_detected"
    if test_status == "passed":
        return "approved_with_notes"
    return "needs_changes"


def _summary(verdict: str, test_status: str, diff_stats: dict[str, Any]) -> str:
    if verdict == "needs_changes" and test_status == "failed":
        return "Tests are failing, so the change needs follow-up before delivery integration."
    if verdict == "no_changes_detected":
        return "No code diff was detected in the upstream artifacts."
    if verdict == "approved_with_notes":
        return (
            f"Tests passed and a non-empty diff was detected "
            f"({diff_stats.get('files_changed', 0)} files changed)."
        )
    return "ReviewGate could not establish a clean approval signal from the provided artifacts."


def _risks(verdict: str, test_status: str, diff_stats: dict[str, Any]) -> list[str]:
    risks: list[str] = []
    if test_status == "failed":
        risks.append("Automated tests reported failure.")
    if test_status == "unknown":
        risks.append("Test status could not be determined from the provided artifacts.")
    if not diff_stats.get("has_changes"):
        risks.append("No code changes were detected for review.")
    if verdict == "approved_with_notes":
        risks.append("Human reviewer should confirm the diff scope matches the approved solution design.")
    return risks


def _checklist(
    test_status: str,
    diff_stats: dict[str, Any],
    selected: dict[str, ArtifactRef],
) -> list[dict[str, Any]]:
    return [
        {
            "item": "Code diff present",
            "passed": bool(diff_stats.get("has_changes")),
            "detail": f"{diff_stats.get('files_changed', 0)} files changed",
        },
        {
            "item": "Tests passed",
            "passed": test_status == "passed",
            "detail": test_status,
        },
        {
            "item": "Technical design available",
            "passed": "technical_design" in selected,
            "detail": selected.get("technical_design").path if selected.get("technical_design") else None,
        },
        {
            "item": "Machine review result generated",
            "passed": True,
            "detail": "review_result.json",
        },
    ]


def _render_report(review_result: dict[str, Any]) -> str:
    checklist = "\n".join(
        f"- [{'x' if item.get('passed') else ' '}] {item.get('item')}: {item.get('detail') or ''}"
        for item in review_result["checklist"]
    )
    risks = "\n".join(f"- {risk}" for risk in review_result["risks"]) or "- No deterministic risks detected."
    artifacts = "\n".join(
        f"- `{artifact['name']}` ({artifact['type']}): {artifact['path']}"
        for artifact in review_result["upstream_artifacts"]
    ) or "- No upstream artifacts provided."
    diff_stats = review_result["diff_stats"]
    return f"""# ReviewGate Report

## Verdict

{review_result["verdict"]}

## Summary

{review_result["summary"]}

## Test Status

{review_result["test_status"]}

## Diff Stats

- Files changed: {diff_stats.get("files_changed", 0)}
- Lines added: {diff_stats.get("lines_added", 0)}
- Lines deleted: {diff_stats.get("lines_deleted", 0)}

## Checklist

{checklist}

## Risks

{risks}

## Upstream Artifacts

{artifacts}
"""


def _requires_human_approval(options: dict[str, Any]) -> bool:
    if _bool_option(options, "auto_approve", False):
        return False
    return _bool_option(options, "requires_approval", True)


def _bool_option(options: dict[str, Any], key: str, default: bool) -> bool:
    value = options.get(key, default)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _merge_recommendation(verdict: str) -> str:
    if verdict == "approved_with_notes":
        return "approve_with_notes"
    if verdict == "no_changes_detected":
        return "blocked"
    return "changes_requested"
