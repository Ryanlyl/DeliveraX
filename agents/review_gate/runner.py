from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, cast

from .io_utils import read_json, read_text, resolve_path_maybe_relative, write_json, write_text
from .llm import ChatLLM, load_llm_config
from .prompts import FINAL_AGGREGATION_SYSTEM, finalize_status_note, review_round_system
from .redact import redact_sensitive_text
from .schemas import ReviewResultPayload, empty_result


def _max_llm_calls() -> int:
    raw = os.getenv("CODEREVIEW_LLM_MAX_CALLS", "").strip()
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return max(1, _int_fallback(os.getenv("CODETEST_LLM_MAX_CALLS", "12"), 12))


def _int_fallback(raw: str, default: int) -> int:
    try:
        return max(1, int(raw))
    except ValueError:
        return default


def _diff_chunk_lines() -> int:
    return max(50, _int_fallback(os.getenv("CODEREVIEW_DIFF_CHUNK_LINES", "350"), 350))


def _parse_json_block(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return cast(dict[str, Any], json.loads(text))


def _truncate(s: str, max_chars: int) -> tuple[str, bool]:
    if len(s) <= max_chars:
        return s, False
    return s[: max_chars - 30] + "\n...(truncated)...\n", True


def _chunk_diff(diff_text: str, max_lines: int) -> list[tuple[int, int, str]]:
    """Return list of (start_line_1based, end_line_inclusive, chunk_body)."""
    lines = diff_text.splitlines()
    if not lines:
        return [(1, 1, "(empty diff)")]
    chunks: list[tuple[int, int, str]] = []
    i = 0
    idx = 0
    total = len(lines)
    while i < total:
        j = min(i + max_lines, total)
        idx += 1
        body = "\n".join(lines[i:j])
        chunks.append((i + 1, j, body))
        i = j
    return chunks


def resolve_inputs_state(
    *,
    codegen_result_path: str | None,
    design_path_cli: str | None,
    diff_path_cli: str | None,
    test_result_path: str,
    requirement_path_cli: str | None,
    task_id_cli: str | None,
) -> tuple[dict[str, Any], dict[str, str | None]]:
    """Return (parsed partial state, warnings list container - use mutable list in caller).

    Resolved dict keys: design_path, diff_path, task_id, codegen_result_path, requirement_path.
    """
    warnings: list[str] = []

    cg_path_raw = codegen_result_path
    cg_base = Path(str(cg_path_raw)).resolve().parent if cg_path_raw else None
    cg: dict[str, Any] | None = None
    if cg_path_raw:
        p = Path(str(cg_path_raw)).resolve()
        if p.is_file():
            cg = read_json(str(p))
        else:
            warnings.append(f"codegen_result not found (ignored): {p}")

    def from_cg(key: str) -> str | None:
        if not cg:
            return None
        v = cg.get(key)
        return str(v).strip() if isinstance(v, str) and str(v).strip() else None

    design_from_cg = None
    diff_from_cg = None
    task_from_cg = None
    if cg_base and cg:
        design_from_cg = resolve_path_maybe_relative(from_cg("technical_design_path"), cg_base)
        diff_from_cg = resolve_path_maybe_relative(from_cg("diff_path"), cg_base)

    task_from_cg = from_cg("task_id")

    design = (design_path_cli or "").strip() or (design_from_cg or "")
    diff_p = (diff_path_cli or "").strip() or (diff_from_cg or "")
    task_id = (task_id_cli or "").strip() or (task_from_cg or "")

    requirement = (requirement_path_cli or "").strip()
    req_resolved = str(Path(requirement).resolve()) if requirement and Path(requirement).is_file() else None

    errs: list[str] = []
    if not Path(test_result_path).is_file():
        errs.append(f"test result not found: {test_result_path}")
    else:
        tr = Path(test_result_path).resolve()
        test_result_path = str(tr)

    if not task_id:
        if Path(test_result_path).is_file():
            data = read_json(test_result_path)
            tid = str(data.get("task_id") or "").strip()
            if tid:
                task_id = tid
    if not task_id:
        errs.append("task_id is required (--task-id or codegen_result/task_id inside code_test_result)")

    if not design or not Path(design).is_file():
        errs.append(f"design not found (--design): {design or '(empty)'}")
    else:
        design = str(Path(design).resolve())

    if not diff_p or not Path(diff_p).is_file():
        errs.append(f"diff not found (--diff): {diff_p or '(empty)'}")
    else:
        diff_p = str(Path(diff_p).resolve())

    if cg and cg_base and diff_from_cg and (diff_path_cli or "").strip():
        expected = resolve_path_maybe_relative(from_cg("diff_path"), cg_base)
        if expected and Path(diff_path_cli.strip()).exists():
            exp_abs = Path(str(expected)).resolve()
            cli_abs = Path(diff_path_cli.strip()).resolve()
            if exp_abs != cli_abs:
                warnings.append(
                    f"codegen_result.diff_path ({exp_abs}) differs from CLI --diff ({cli_abs}); "
                    "using CLI (--diff wins per findings)."
                )
    if cg and cg_base and design_from_cg and (design_path_cli or "").strip():
        expected_d_abs = resolve_path_maybe_relative(from_cg("technical_design_path"), cg_base)
        dp_cli = Path(design_path_cli.strip()).resolve()
        if expected_d_abs and Path(design_path_cli.strip()).exists():
            if dp_cli != Path(str(expected_d_abs)).resolve():
                warnings.append(
                    "codegen_result.technical_design_path differs from CLI --design; using CLI (--design wins)."
                )

    errors = errs if errs else []
    state: dict[str, Any] = {
        "errors": errors,
        "warnings_resolve": warnings,
        "design_path": design if not errors else design,
        "diff_path": diff_p,
        "test_result_path": test_result_path if not errs or Path(test_result_path).is_file() else test_result_path,
        "task_id": task_id if not errors else (task_id or "unknown-task"),
        "requirement_path": req_resolved,
        "codegen_result_path_used": str(Path(cg_path_raw).resolve())
        if cg_path_raw and Path(str(cg_path_raw)).exists()
        else None,
        "design_path_cli": design_path_cli,
        "diff_path_cli": diff_path_cli,
        "design_from_codegen": bool(design_from_cg),
        "diff_from_codegen": bool(diff_from_cg),
        "parsed_codegen": cg,
    }
    if errors:

        design_for_err = ""
        dp = Path(design_path_cli) if design_path_cli else None
        if dp and dp.is_file():
            design_for_err = str(dp.resolve())
        diff_err = ""
        if diff_path_cli and Path(diff_path_cli).is_file():
            diff_err = str(Path(diff_path_cli).resolve())
        state.update(
            {
                "design_path": design_for_err,
                "diff_path": diff_err,
            }
        )
    return state, {"errors": "; ".join(errors) if errors else ""}


def _test_excerpt(payload: dict[str, Any]) -> tuple[str, str]:
    """Return (risk_note excerpt, condensed test blob)."""
    status = str(payload.get("status", "")).lower()
    summary = str(payload.get("summary", "") or "")
    stdout_t = redact_sensitive_text(str(payload.get("stdout_tail", "") or ""))
    stderr_t = redact_sensitive_text(str(payload.get("stderr_tail", "") or ""))

    ct = ""
    if status == "passed":
        risk = ""
    elif status in {"fail", "failed", "failure"}:
        risk = (
            "Tests did not pass. Treat implementation + tests as questionable until rerun green. "
            f"Upstream summary: {summary}"
        )
    elif status == "test":
        risk = 'Upstream code_test status is "test" (smoke); not a formal pass for delivery gates.'
        ct = stdout_t[-4000:] if stdout_t else ""
    else:
        risk = f"Non-pass test snapshot (status={status}). Summary: {summary}"
        ct = stdout_t[-6000:] if stdout_t else ""

    condensed = ""
    condensed += json.dumps({"code_test.status": payload.get("status"), "summary": summary[:2000]}, ensure_ascii=False)

    condensed += (
        "\n--- stdout_tail (redacted excerpt) ---\n"
        + _truncate(stdout_t, 9000)[0]
        + "\n--- stderr_tail (redacted excerpt) ---\n"
        + _truncate(stderr_t, 4000)[0]
    )

    lp = payload.get("log_path")
    if lp and isinstance(lp, str):
        lg = Path(lp)
        if lg.is_file():
            try:
                body = lg.read_text(encoding="utf-8", errors="replace")[-4500:]
                condensed += (
                    "\n--- test_run.log excerpt (EOF, redacted) ---\n"
                    + redact_sensitive_text(body)
                    + "\n"
                )
            except OSError:
                pass

    return risk.strip(), condensed


def _derive_top_level_status(
    *,
    merge_recommendation: str,
    has_blocker: bool,
    has_major: bool,
) -> tuple[str, str]:
    """Return (normalized merge_recommendation, status for DI)."""
    mr = merge_recommendation.strip().lower().replace("-", "_")

    mr_norm_map = {
        "approve": "approve",
        "approve_with_nits": "approve_with_nits",
        "changerequest": "changes_requested",
        "changes_requested": "changes_requested",
        "blocked": "blocked",
        "reject": "rejected",
        "rejected": "rejected",
    }
    if mr in mr_norm_map:
        nm = mr_norm_map[mr]
    elif "nit" in mr:
        nm = "approve_with_nits"
    else:
        nm = "changes_requested"

    if nm == "blocked" or has_blocker:
        return "blocked", "changes_requested"
    if nm == "rejected":
        return "rejected", "rejected"
    if nm == "approve_with_nits":
        # pipeline may insist major still blocks delivery
        if has_major:
            return "blocked", "changes_requested"
        return nm, "approved"
    if nm == "approve":
        if has_major:
            return "changes_requested", "changes_requested"
        return nm, "approved"

    # changes_requested
    return nm, "changes_requested"


def _finalize_merge_and_status(payload: dict[str, Any]) -> None:
    issues = payload.get("issues") or []
    mr_in = str(payload.get("merge_recommendation") or "changes_requested")
    blocker = False
    major_h = False
    for item in issues:
        if isinstance(item, dict):
            sv = str(item.get("severity", "")).lower()
            if sv == "blocker":
                blocker = True
            elif sv == "major":
                major_h = True
    mr_adj, stat = _derive_top_level_status(
        merge_recommendation=mr_in, has_blocker=blocker, has_major=major_h
    )
    payload["merge_recommendation"] = mr_adj
    payload["status"] = stat


def _human_markdown(report: ReviewResultPayload) -> str:
    lines = ["# Code review report\n", "## Summary\n\n", report.get("summary") or "(none)", "\n"]
    rn = report.get("risk_note")
    if rn:
        lines.extend(["\n## Risk note\n\n", rn, "\n"])
    lines.extend(
        [
            "\n## Gate fields\n\n",
            f"- `status` (delivery integration): **{report.get('status')}**\n",
            f"- `merge_recommendation` (agent): **{report.get('merge_recommendation')}**\n",
            "\n## Issues\n\n",
        ]
    )
    for i, issue in enumerate(report.get("issues") or [], 1):
        if isinstance(issue, dict):
            lines.append(
                f"{i}. **[{issue.get('severity')}] {issue.get('category')}** — `{issue.get('file')}`\n\n"
                f"   Evidence: {(issue.get('evidence') or '')[:2400]}\n\n"
                f"   Suggestion: {issue.get('fix_suggestion') or ''}\n\n"
            )
    lines.extend(["## Test gaps\n\n"])
    for g in report.get("test_gaps") or []:
        if isinstance(g, dict):
            lines.append(f"- {(g.get('summary') or '')}\n\n  `(suggested: {g.get('suggested_test')})`\n\n")
    wf = report.get("warnings") or []
    if wf:
        lines.extend(["## Warnings\n\n", "\n".join(f"- {w}" for w in wf), "\n"])
    return "".join(lines)


def _feedback_markdown(report: ReviewResultPayload) -> str:
    parts = ["# Feedback for repair (CodeGen / CodeTest)\n\n"]
    parts.append(report.get("summary") or "")
    parts.append("\n\n---\n")
    idx = 0
    for issue in report.get("issues") or []:
        if isinstance(issue, dict):
            idx += 1
            parts.append(
                f"\n## Finding {idx}\n"
                f"- severity: `{issue.get('severity')}`\n"
                f"- category: `{issue.get('category')}`\n"
                f"- file: `{issue.get('file')}`\n"
                f"- evidence:\n```\n{redact_sensitive_text(str(issue.get('evidence') or '')[:2800])}\n```\n"
                f"- suggested_fix:\n{issue.get('fix_suggestion') or ''}\n"
            )
    for tg in report.get("test_gaps") or []:
        if isinstance(tg, dict):
            parts.append(
                f"\n## Test gap\n- {tg.get('summary')}\n- propose: {tg.get('suggested_test')}\n"
            )
    return "".join(parts)


def run_codereview(
    *,
    codegen_result_path: str | None,
    design_path_cli: str | None,
    diff_path_cli: str | None,
    test_result_path: str,
    requirement_path_cli: str | None,
    task_id_cli: str | None,
    output_dir: str,
    policy_pack_path: str | None,
    local_only: bool,
    max_llm_calls_override: int | None = None,
) -> ReviewResultPayload:
    warnings: list[str] = []
    caps = max_llm_calls_override if max_llm_calls_override is not None else _max_llm_calls()
    merged = resolve_inputs_state(
        codegen_result_path=codegen_result_path,
        design_path_cli=design_path_cli,
        diff_path_cli=diff_path_cli,
        test_result_path=test_result_path,
        requirement_path_cli=requirement_path_cli,
        task_id_cli=task_id_cli,
    )
    state_any, _meta = merged
    warnings.extend(state_any.get("warnings_resolve") or [])
    errs = cast(list[str], state_any.get("errors") or [])
    if errs:
        tid_e = str(state_any.get("task_id") or "unknown-task")
        base_t = dict(empty_result(task_id=tid_e, local_only=False))
        base_t["warnings"] = warnings + [f"resolve_error: {e}" for e in errs]
        base_t["errors"] = errs
        base_t["design_path"] = str(state_any.get("design_path") or "")
        base_t["diff_path"] = str(state_any.get("diff_path") or "")
        base_t["test_result_path"] = str(state_any.get("test_result_path") or "")
        base_t["status"] = "changes_requested"
        base_t["merge_recommendation"] = "blocked"
        base_t["summary"] = "Inputs invalid; skipped LLM steps."
        base_t.setdefault("issues", []).append(
            {
                "id": "CR-RESOLVE-1",
                "severity": "blocker",
                "category": "convention",
                "file": "",
                "line": None,
                "evidence": "; ".join(errs),
                "fix_suggestion": "Fix --design, --diff, --test-result (or valid --codegen-result).",
            }
        )
        out_er = Path(output_dir).resolve() / tid_e
        out_er.mkdir(parents=True, exist_ok=True)
        json_er = str(out_er / "code_review_result.json")
        base_t["result_json_path"] = json_er
        base_t["code_review_report_path"] = str(out_er / "code_review_report.md")
        base_t["feedback_review_path"] = str(out_er / "feedback_review.md")
        write_json(json_er, base_t)
        write_text(str(out_er / "code_review_report.md"), _human_markdown(cast(ReviewResultPayload, base_t)))
        write_text(str(out_er / "feedback_review.md"), _feedback_markdown(cast(ReviewResultPayload, base_t)))
        return cast(ReviewResultPayload, base_t)

    task_id = cast(str, state_any["task_id"])
    design_path = cast(str, state_any["design_path"])
    diff_path_p = cast(str, state_any["diff_path"])
    test_path = cast(str, state_any["test_result_path"])

    req_path = state_any.get("requirement_path")

    policy_extra = ""
    if policy_pack_path and Path(policy_pack_path).is_file():
        policy_extra = read_text(policy_pack_path)
        warnings.append(f"policy_pack loaded: {Path(policy_pack_path).resolve().as_posix()}")

    out_root = Path(output_dir).resolve() / task_id
    out_root.mkdir(parents=True, exist_ok=True)
    json_out = str(out_root / "code_review_result.json")
    md_out = str(out_root / "code_review_report.md")
    fb_out = str(out_root / "feedback_review.md")

    test_payload = read_json(test_path)
    risk_note, test_blob = _test_excerpt(test_payload)

    if local_only:
        rep = empty_result(task_id=task_id, local_only=True)
        rep.update(
            {
                "design_path": design_path,
                "diff_path": diff_path_p,
                "test_result_path": test_path,
                "requirement_path": str(req_path or ""),
                "codegen_result_path": str(codegen_result_path or "")
                if codegen_result_path
                else None,
                "policy_pack_path": policy_pack_path,
                "summary": "Local-only smoke: skipped LLM. Configure API key for automated review.",
                "status": "test",
                "merge_recommendation": "approve_with_nits",
                "risk_note": risk_note,
                "warnings": warnings + ["local_only:true"],
                "max_llm_calls": caps,
                "code_review_report_path": md_out,
                "feedback_review_path": fb_out,
                "result_json_path": json_out,
                "prompt_schema_version": "codereview-v1-local",
            }
        )
        write_json(json_out, dict(rep))
        write_text(md_out, _human_markdown(rep))
        write_text(fb_out, "(local-only stub)\n")
        return rep

    diff_text_orig = read_text(diff_path_p)
    design_text_orig = read_text(design_path)
    design_trunc, dt_flag = _truncate(design_text_orig, 52000)

    cfg = load_llm_config()
    llm = ChatLLM(cfg)
    if not llm.available:
        raise RuntimeError("LLM not configured — set API key env or retry with --local-only.")

    req_excerpt = ""
    if isinstance(req_path, str) and req_path and Path(req_path).is_file():
        req_excerpt, _ = _truncate(read_text(req_path), 12000)

    llm_calls = 0

    partial_issues_all: list[dict[str, Any]] = []
    partial_gaps_all: list[dict[str, Any]] = []

    def bump() -> None:
        nonlocal llm_calls
        llm_calls += 1
        if llm_calls > caps:
            raise RuntimeError(f"LLM budget exceeded ({caps}). Increase --max-llm-calls or env.")

    max_lines_chunk = _diff_chunk_lines()
    chunks_tuples = _chunk_diff(redact_sensitive_text(diff_text_orig), max_lines_chunk)

    rounds = len(chunks_tuples)
    warnings.append(f"diff_chunks_scheduled:{rounds} (chunk_lines≤{max_lines_chunk})")

    system_chunk = review_round_system(policy_extra)
    dt_warn = "(design truncated)" if dt_flag else ""
    for chunk_idx, (start_ln, end_ln, chunk_body) in enumerate(chunks_tuples):
        tb_trunc, tb_flag = _truncate(test_blob, 12000)
        user = (
            f"DIFF chunk_lines {start_ln}-{end_ln} of unified diff ({chunk_idx + 1}/{rounds})\n\n"
            f"{chunk_body}\n\n---\nDesign excerpt ({dt_warn}):\n{design_trunc}\n\n---\n"
            f"Requirement excerpt:\n{(req_excerpt[:8000])}\n---\ncode_test context (possibly truncated):\n{tb_trunc}\n"
            f"{finalize_status_note()}"
        )
        if tb_flag:
            warnings.append("test_context_truncated:true")
        bump()
        raw = llm.complete(system=system_chunk, user=user)
        data = _parse_json_block(redact_sensitive_text(raw))
        for it in list(data.get("partial_issues") or []):
            if isinstance(it, dict):
                partial_issues_all.append(dict(it))
        for tg in list(data.get("partial_test_gaps") or []):
            if isinstance(tg, dict):
                partial_gaps_all.append(dict(tg))

    merge_user = json.dumps(
        {"partial_issues": partial_issues_all, "partial_test_gaps": partial_gaps_all}, ensure_ascii=False
    )

    aggregation_user = (
        merge_user[:110_000]
        + "\n\nNow produce the FINAL consolidated JSON matching schema described in FINAL_AGGREGATION_SYSTEM. "
        f"risk_note_guidance:{risk_note}"
    )

    bump()
    final_raw = llm.complete(system=FINAL_AGGREGATION_SYSTEM, user=aggregation_user)
    payload = _parse_json_block(redact_sensitive_text(final_raw))

    summary = redact_sensitive_text(str(payload.get("summary") or "Review summary missing."))

    mr = str(payload.get("merge_recommendation") or "").strip()

    raw_issues_out = payload.get("issues") or []
    normalized_issues_out: list[dict[str, Any]] = []

    nid = 0
    pattern = re.compile(r"^[A-Za-z0-9_.\-]+$")
    for idx, raw_is in enumerate(raw_issues_out):
        if not isinstance(raw_is, dict):
            continue
        nid += 1
        rid_raw = raw_is.get("id")
        if isinstance(rid_raw, str) and rid_raw.strip() and pattern.match(rid_raw.strip()):
            fid = rid_raw.strip()
        elif isinstance(rid_raw, str) and rid_raw.strip():
            fid = f"CR-{nid}-{rid_raw.strip()[:32]}"
        else:
            fid = f"CR-{nid}"
        sev_raw = raw_is.get("severity")
        normalized_issues_out.append(
            {
                "id": fid,
                "severity": str(sev_raw or "minor").lower(),
                "category": str(raw_is.get("category") or "convention"),
                "file": str(raw_is.get("file") or ""),
                "line": raw_is["line"]
                if isinstance(raw_is.get("line"), int) or raw_is.get("line") is None
                else None,
                "evidence": redact_sensitive_text(str(raw_is.get("evidence") or "")),
                "fix_suggestion": redact_sensitive_text(str(raw_is.get("fix_suggestion") or "")),
            }
        )

    raw_gaps = payload.get("test_gaps") or []
    out_gaps: list[dict[str, Any]] = []
    if isinstance(raw_gaps, list):
        for tg in raw_gaps:
            if isinstance(tg, dict):
                out_gaps.append(
                    {
                        "summary": redact_sensitive_text(str(tg.get("summary") or "")[:2400]),
                        "suggested_test": redact_sensitive_text(str(tg.get("suggested_test") or "")[:4800]),
                    }
                )

    rep = ReviewResultPayload(
        schema_version="1.0",
        prompt_schema_version="codereview-v1",
        task_id=task_id,
        summary=summary,
        merge_recommendation=(mr.lower() if mr else "changes_requested"),
        risk_note=risk_note,
        local_only=False,
        llm_calls=llm_calls,
        max_llm_calls=caps,
        design_path=design_path,
        diff_path=diff_path_p,
        test_result_path=test_path,
        requirement_path=str(req_path) if req_path else "",
        codegen_result_path=str(Path(codegen_result_path).resolve())
        if codegen_result_path and Path(codegen_result_path).exists()
        else None,
        policy_pack_path=policy_pack_path or "",
        issues=normalized_issues_out,
        test_gaps=out_gaps,
        warnings=warnings.copy(),
        code_review_report_path=md_out,
        feedback_review_path=fb_out,
        result_json_path=json_out,
    )

    rep_dict = cast(dict[str, Any], dict(rep))
    _finalize_merge_and_status(rep_dict)

    write_json(json_out, rep_dict)
    final_payload = cast(ReviewResultPayload, rep_dict)
    write_text(md_out, _human_markdown(final_payload))
    write_text(fb_out, redact_sensitive_text(_feedback_markdown(final_payload)))
    return final_payload


def outcome_exit_code(report: ReviewResultPayload) -> int:
    """Exit 2 only when any issue has severity blocker (frozen acceptance §8.3)."""
    for it in report.get("issues") or []:
        if isinstance(it, dict) and str(it.get("severity", "")).lower() == "blocker":
            return 2
    return 0
