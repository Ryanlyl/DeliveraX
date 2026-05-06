from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from api_server.schemas import PipelineRecord, StageRecord
from api_server.storage.json_store import JsonPipelineStore


def test_json_store_round_trips_pipeline() -> None:
    tmp_root = Path(__file__).resolve().parents[2] / "tmp" / "api_server_tests" / uuid4().hex
    tmp_root.mkdir(parents=True, exist_ok=True)
    store = JsonPipelineStore(tmp_root)
    pipeline = PipelineRecord(
        id="demo",
        name="Demo Pipeline",
        requirement="Make the completion button more visible.",
        stages=[StageRecord(id="requirements", name="需求分析", agent="ReqAnalysis")],
    )

    try:
        store.save(pipeline)
        loaded = store.get("demo")

        assert loaded.id == "demo"
        assert loaded.stages[0].id == "requirements"
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
