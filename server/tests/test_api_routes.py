from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

fastapi = pytest.importorskip("fastapi")
testclient = pytest.importorskip("fastapi.testclient")


def test_api_exposes_health_stages_and_pipeline_creation(monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    artifacts_root = repo_root / "tmp" / "api_server_tests" / uuid4().hex
    monkeypatch.setenv("DELIVERAX_REPO_ROOT", str(repo_root))
    monkeypatch.setenv("DELIVERAX_ARTIFACTS_ROOT", str(artifacts_root))

    from api_server.config import get_settings
    from api_server.main import create_app

    get_settings.cache_clear()
    app = create_app()
    client = testclient.TestClient(app)

    health_response = client.get("/health")
    stages_response = client.get("/api/stages")
    pipeline_response = client.post(
        "/api/pipelines",
        json={
            "pipeline_id": "api-demo",
            "requirement": "请生成一个任务列表页面需求。",
        },
    )

    assert health_response.status_code == 200
    assert stages_response.status_code == 200
    assert pipeline_response.status_code == 200
    assert pipeline_response.json()["id"] == "api-demo"
