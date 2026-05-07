from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from agents.release_integration.upstream_results import (
    assert_review_approved,
    assert_test_passed,
    load_review_result,
    load_test_result,
)


def test_load_test_result_accepts_soft_passed_non_critical_failure() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    tmp_root = repo_root / "tmp" / "api_server_tests" / uuid4().hex
    tmp_root.mkdir(parents=True, exist_ok=True)
    test_result_path = tmp_root / "code_test_result.json"
    test_result_path.write_text(
        json.dumps(
            {
                "status": "failed",
                "validation_error_code": "TEST_GENERATION_MISMATCH",
                "environment_error_code": "",
                "errors": ["selector mismatch"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    try:
        result = load_test_result(result_path=str(test_result_path), explicit_status=None)
        assert result["status"] == "passed"
        assert_test_passed(result)
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


def test_load_test_result_rejects_soft_pass_when_environment_failed() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    tmp_root = repo_root / "tmp" / "api_server_tests" / uuid4().hex
    tmp_root.mkdir(parents=True, exist_ok=True)
    test_result_path = tmp_root / "code_test_result.json"
    test_result_path.write_text(
        json.dumps(
            {
                "status": "failed",
                "validation_error_code": "TEST_GENERATION_MISMATCH",
                "environment_error_code": "DEP_INSTALL_FAILED",
                "errors": ["dependency install failed"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    try:
        result = load_test_result(result_path=str(test_result_path), explicit_status=None)
        with pytest.raises(RuntimeError, match="Upstream code test is not passed"):
            assert_test_passed(result)
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


def test_load_review_result_accepts_approved_with_notes_status() -> None:
    result = load_review_result(result_path=None, explicit_status="approved_with_notes")
    assert_review_approved(result)


def test_load_review_result_rejects_changes_requested() -> None:
    result = load_review_result(result_path=None, explicit_status="needs_changes")
    with pytest.raises(RuntimeError, match="Upstream code review is not approved"):
        assert_review_approved(result)
