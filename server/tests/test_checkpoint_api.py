from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from stage_contracts import ArtifactRef

fastapi = pytest.importorskip("fastapi")
testclient = pytest.importorskip("fastapi.testclient")


def test_current_checkpoint_api_and_approve(monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    artifacts_root = repo_root / "tmp" / "api_server_tests" / uuid4().hex
    monkeypatch.setenv("DELIVERAX_REPO_ROOT", str(repo_root))
    monkeypatch.setenv("DELIVERAX_ARTIFACTS_ROOT", str(artifacts_root))

    from api_server.config import get_settings
    from api_server.main import create_app

    get_settings.cache_clear()
    app = create_app()
    client = testclient.TestClient(app)

    pipeline_id = "checkpoint-api-demo"
    response = client.post(
        "/api/pipelines",
        json={"pipeline_id": pipeline_id, "requirement": "demo"},
    )
    assert response.status_code == 200

    artifact_path = artifacts_root / pipeline_id / "solution" / "technical_design.md"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("# Design\n", encoding="utf-8")

    pipeline = app.state.pipeline_service.get(pipeline_id)
    solution = next(stage for stage in pipeline.stages if stage.id == "solution")
    solution.status = "pending_approval"
    solution.run_id = "solution-run"
    solution.output_artifacts = [
        ArtifactRef(name="technical_design", type="markdown", path=str(artifact_path), role="handoff")
    ]
    solution.human_output = "# Design\n"
    app.state.pipeline_store.save(pipeline)

    current = client.get(f"/api/pipelines/{pipeline_id}/checkpoints/current")
    assert current.status_code == 200
    payload = current.json()
    checkpoint_id = payload["checkpoint"]["id"]
    assert payload["checkpoint"]["stage_id"] == "solution"
    assert payload["checkpoint"]["title"] == "方案设计审批"
    assert payload["stage"]["status"] == "pending_approval"
    assert payload["human_output"] == "# Design\n"
    assert payload["artifacts"][0]["name"] == "technical_design"

    approved = client.post(
        f"/api/checkpoints/{checkpoint_id}/approve",
        json={"reviewer": "qa", "comment": "Looks good", "continue_pipeline": False},
    )
    assert approved.status_code == 200
    updated = approved.json()
    solution = next(stage for stage in updated["stages"] if stage["id"] == "solution")
    assert solution["status"] == "succeeded"

    checkpoint = app.state.checkpoint_service._load(checkpoint_id)  # noqa: SLF001
    assert checkpoint.status == "approved"
    assert checkpoint.reviewer == "qa"


def test_legacy_stage_approve_api_delegates_to_checkpoint_service(monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    artifacts_root = repo_root / "tmp" / "api_server_tests" / uuid4().hex
    monkeypatch.setenv("DELIVERAX_REPO_ROOT", str(repo_root))
    monkeypatch.setenv("DELIVERAX_ARTIFACTS_ROOT", str(artifacts_root))

    from api_server.config import get_settings
    from api_server.main import create_app

    get_settings.cache_clear()
    app = create_app()
    client = testclient.TestClient(app)

    pipeline_id = "legacy-approve-demo"
    client.post("/api/pipelines", json={"pipeline_id": pipeline_id, "requirement": "demo"})

    pipeline = app.state.pipeline_service.get(pipeline_id)
    solution = next(stage for stage in pipeline.stages if stage.id == "solution")
    solution.status = "pending_approval"
    app.state.pipeline_store.save(pipeline)

    response = client.post(
        f"/api/pipelines/{pipeline_id}/stages/solution/approve",
        json={"reviewer": "legacy", "comment": "approved"},
    )
    assert response.status_code == 200
    solution = next(stage for stage in response.json()["stages"] if stage["id"] == "solution")
    assert solution["status"] == "succeeded"

    checkpoint = app.state.checkpoint_service._find_latest_for_stage(  # noqa: SLF001
        pipeline_id,
        "solution",
        status="approved",
    )
    assert checkpoint is not None
    assert checkpoint.status == "approved"


def test_legacy_stage_reject_api_delegates_to_checkpoint_service(monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    artifacts_root = repo_root / "tmp" / "api_server_tests" / uuid4().hex
    monkeypatch.setenv("DELIVERAX_REPO_ROOT", str(repo_root))
    monkeypatch.setenv("DELIVERAX_ARTIFACTS_ROOT", str(artifacts_root))

    from api_server.config import get_settings
    from api_server.main import create_app

    get_settings.cache_clear()
    app = create_app()
    client = testclient.TestClient(app)

    pipeline_id = "legacy-reject-demo"
    client.post("/api/pipelines", json={"pipeline_id": pipeline_id, "requirement": "demo"})

    test_artifact = artifacts_root / pipeline_id / "test" / "code_test_result.json"
    test_artifact.parent.mkdir(parents=True, exist_ok=True)
    test_artifact.write_text('{"status": "passed"}\n', encoding="utf-8")

    pipeline = app.state.pipeline_service.get(pipeline_id)
    test_stage = next(stage for stage in pipeline.stages if stage.id == "test")
    review_stage = next(stage for stage in pipeline.stages if stage.id == "review")
    test_stage.status = "succeeded"
    test_stage.output_artifacts = [
        ArtifactRef(name="code_test_result", type="json", path=str(test_artifact), role="machine")
    ]
    review_stage.status = "pending_approval"
    app.state.pipeline_store.save(pipeline)

    response = client.post(
        f"/api/pipelines/{pipeline_id}/stages/review/reject",
        json={"reviewer": "legacy", "comment": "needs another pass"},
    )

    assert response.status_code == 200
    stages = response.json()["stages"]
    review_stage = next(stage for stage in stages if stage["id"] == "review")
    test_stage = next(stage for stage in stages if stage["id"] == "test")
    assert review_stage["status"] == "rejected"
    assert test_stage["status"] == "queued"
    assert test_stage["data"]["rerun_required"] is True
    assert test_stage["data"]["rerun_input_artifacts"][0]["name"] == "reject_reason"

    checkpoint = app.state.checkpoint_service._find_latest_for_stage(  # noqa: SLF001
        pipeline_id,
        "review",
        status="rejected",
    )
    assert checkpoint is not None
    assert checkpoint.reject_reason == "needs another pass"
