from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _ensure_import_paths(root: Path) -> None:
    candidates = [root, root / "server"]
    for item in candidates:
        text = str(item)
        if text not in sys.path:
            sys.path.insert(0, text)


class SmokeResult:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.count = 0

    def check(self, condition: bool, message: str) -> None:
        self.count += 1
        if condition:
            print(f"PASS [{self.count}] {message}")
            return
        print(f"FAIL [{self.count}] {message}")
        self.failures.append(message)

    def finish(self) -> int:
        if self.failures:
            print("")
            print("Smoke result: FAIL")
            print(f"Failed checks: {len(self.failures)}")
            for item in self.failures:
                print(f"- {item}")
            return 1
        print("")
        print(f"Smoke result: PASS ({self.count} checks)")
        return 0


def _as_json(resp: Any) -> dict[str, Any]:
    payload = resp.json()
    if isinstance(payload, dict):
        return payload
    raise AssertionError(f"Expected JSON object, got: {type(payload)!r}")


def _create_project(client: TestClient, *, name: str, github_url: str) -> dict[str, Any]:
    resp = client.post(
        "/api/projects",
        json={
            "name": name,
            "description": f"{name} smoke project",
            "github_url": github_url,
        },
    )
    if resp.status_code != 200:
        raise AssertionError(f"Create project failed: {resp.status_code} {resp.text}")
    return _as_json(resp)


def _create_pipeline(
    client: TestClient,
    *,
    requirement: str,
    project_id: str | None = None,
) -> Any:
    body: dict[str, Any] = {
        "name": "Smoke Pipeline",
        "requirement": requirement,
    }
    if project_id is not None:
        body["project_id"] = project_id
    return client.post("/api/pipelines", json=body)


def main() -> int:
    root = _repo_root()
    _ensure_import_paths(root)

    with tempfile.TemporaryDirectory(prefix="deliverax_smoke_") as tmpdir:
        artifacts_root = Path(tmpdir) / "artifacts"
        artifacts_root.mkdir(parents=True, exist_ok=True)
        os.environ["DELIVERAX_ARTIFACTS_ROOT"] = str(artifacts_root)

        from api_server.config import get_settings

        get_settings.cache_clear()

        from api_server.main import create_app

        app = create_app()
        result = SmokeResult()

        with TestClient(app) as client:
            project_a = _create_project(
                client,
                name="Smoke Project A",
                github_url="https://github.com/example/project-a",
            )
            project_b = _create_project(
                client,
                name="Smoke Project B",
                github_url="https://github.com/example/project-b",
            )
            project_a_id = str(project_a["id"])
            project_b_id = str(project_b["id"])

            create_a = _create_pipeline(
                client,
                requirement="pipeline for project A",
                project_id=project_a_id,
            )
            result.check(create_a.status_code == 200, "POST /api/pipelines with valid project_id returns 200")
            data_a = _as_json(create_a) if create_a.status_code == 200 else {}
            pipeline_a_id = str(data_a.get("id", ""))
            result.check(data_a.get("project_id") == project_a_id, "PipelineRecord.project_id is saved correctly")

            project_a_latest = client.get(f"/api/projects/{project_a_id}")
            result.check(project_a_latest.status_code == 200, "GET /api/projects/{id} returns 200")
            project_a_body = _as_json(project_a_latest) if project_a_latest.status_code == 200 else {}
            pipeline_ids = project_a_body.get("pipeline_ids", [])
            result.check(
                isinstance(pipeline_ids, list) and pipeline_a_id in pipeline_ids,
                "ProjectRecord.pipeline_ids includes the newly created pipeline",
            )

            create_b = _create_pipeline(
                client,
                requirement="pipeline for project B",
                project_id=project_b_id,
            )
            result.check(create_b.status_code == 200, "Create second project-linked pipeline returns 200")
            data_b = _as_json(create_b) if create_b.status_code == 200 else {}
            pipeline_b_id = str(data_b.get("id", ""))

            standalone = _create_pipeline(client, requirement="standalone pipeline")
            result.check(standalone.status_code == 200, "Create standalone pipeline (no project_id) returns 200")
            data_standalone = _as_json(standalone) if standalone.status_code == 200 else {}
            standalone_id = str(data_standalone.get("id", ""))

            legacy_linked = _create_pipeline(client, requirement="legacy linked via project.pipeline_ids only")
            result.check(legacy_linked.status_code == 200, "Create legacy-style pipeline returns 200")
            data_legacy = _as_json(legacy_linked) if legacy_linked.status_code == 200 else {}
            legacy_id = str(data_legacy.get("id", ""))

            project_for_legacy = app.state.project_store.get(project_a_id)
            if legacy_id not in project_for_legacy.pipeline_ids:
                project_for_legacy.pipeline_ids.append(legacy_id)
                app.state.project_store.save(project_for_legacy)

            list_all = client.get("/api/pipelines")
            result.check(list_all.status_code == 200, "GET /api/pipelines without project_id returns 200")
            all_items = list_all.json() if list_all.status_code == 200 else []
            all_ids = {str(item.get("id")) for item in all_items if isinstance(item, dict)}
            expected_all = {pipeline_a_id, pipeline_b_id, standalone_id, legacy_id}
            result.check(
                expected_all.issubset(all_ids),
                "GET /api/pipelines without project_id returns all created pipelines",
            )

            list_a = client.get(f"/api/pipelines?project_id={project_a_id}")
            result.check(list_a.status_code == 200, "GET /api/pipelines?project_id=A returns 200")
            list_a_items = list_a.json() if list_a.status_code == 200 else []
            list_a_ids = {str(item.get("id")) for item in list_a_items if isinstance(item, dict)}
            result.check(
                list_a_ids == {pipeline_a_id, legacy_id},
                "GET /api/pipelines?project_id=A returns only project-related pipelines",
            )

            list_b = client.get(f"/api/pipelines?project_id={project_b_id}")
            result.check(list_b.status_code == 200, "GET /api/pipelines?project_id=B returns 200")
            list_b_items = list_b.json() if list_b.status_code == 200 else []
            list_b_ids = {str(item.get("id")) for item in list_b_items if isinstance(item, dict)}
            result.check(
                list_b_ids == {pipeline_b_id},
                "GET /api/pipelines?project_id=B excludes unrelated pipelines",
            )

            invalid_project_id = "missing-project-id-smoke"
            post_invalid = _create_pipeline(
                client,
                requirement="invalid project id",
                project_id=invalid_project_id,
            )
            result.check(
                post_invalid.status_code == 404,
                "POST /api/pipelines with non-existent project_id returns 404",
            )

            get_invalid = client.get(f"/api/pipelines?project_id={invalid_project_id}")
            result.check(
                get_invalid.status_code == 404,
                "GET /api/pipelines?project_id=non-existent returns 404",
            )

        return result.finish()


if __name__ == "__main__":
    raise SystemExit(main())
