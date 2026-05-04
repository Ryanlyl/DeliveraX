from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from api_server.schemas import (
    ArtifactListResponse,
    ArtifactTextResponse,
    ArtifactRef,
    ReviewAssetsResponse,
    ReviewAssetItem,
)
from api_server.services.artifact_service import ArtifactNotFoundError, UnsafeArtifactPathError

router = APIRouter(tags=["artifacts"])


def _find_artifact_by_role(artifacts: list[ArtifactRef], role: str, ext: str = "") -> ArtifactRef | None:
    for a in artifacts:
        if a.role == role:
            return a
    if ext:
        for a in artifacts:
            if a.path.endswith(ext):
                return a
    return None


def _find_artifact_by_name(artifacts: list[ArtifactRef], *keywords: str) -> ArtifactRef | None:
    for a in artifacts:
        name_lower = a.name.lower()
        path_lower = a.path.lower()
        for kw in keywords:
            if kw in name_lower or kw in path_lower:
                return a
    return None


def _safe_read(artifact_service, path: str | None) -> ReviewAssetItem | None:
    if not path:
        return None
    try:
        result = artifact_service.read_text(path)
        return ReviewAssetItem(path=result.path, content=result.content)
    except (ArtifactNotFoundError, UnsafeArtifactPathError):
        return None


@router.get(
    "/pipelines/{pipeline_id}/stages/{stage_id}/artifacts",
    response_model=ArtifactListResponse,
    summary="获取 Stage 产物列表",
    description="返回某个 pipeline stage 下的所有输出产物（output_artifacts）和标准产物路径（input, result, manifest, human_output 等）。",
    response_description="产物列表，包含 standard_artifacts 路径映射。",
)
def list_stage_artifacts(pipeline_id: str, stage_id: str, request: Request) -> ArtifactListResponse:
    return request.app.state.artifact_service.list_stage_artifacts(pipeline_id, stage_id)


@router.get(
    "/artifacts/file",
    response_model=ArtifactTextResponse,
    summary="读取产物文件内容",
    description="根据产物路径读取文件文本内容。路径必须在 artifacts_root 范围内。",
    response_description="文件路径与文本内容。",
    responses={
        404: {"description": "ARTIFACT_NOT_FOUND — 文件不存在"},
        400: {"description": "UNSAFE_ARTIFACT_PATH — 路径越界"},
    },
)
def read_artifact_file(request: Request, path: str = Query(...)) -> ArtifactTextResponse:
    try:
        return request.app.state.artifact_service.read_text(path)
    except ArtifactNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {path}") from exc
    except UnsafeArtifactPathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/pipelines/{pipeline_id}/stages/{stage_id}/review-assets",
    response_model=ReviewAssetsResponse,
    summary="获取 Stage 评审资产（聚合接口）",
    description=(
        "返回当前阶段用于前端展示的聚合内容：human_output、diff、review_report 以及全部产物列表。"
        "优先从 standard_artifacts 和 output_artifacts 中自动匹配。"
    ),
    response_description="聚合的评审资产。",
    responses={
        404: {"description": "ARTIFACT_NOT_FOUND"},
    },
)
def get_stage_review_assets(pipeline_id: str, stage_id: str, request: Request) -> ReviewAssetsResponse:
    svc = request.app.state.artifact_service
    list_resp = svc.list_stage_artifacts(pipeline_id, stage_id)

    # human_output: from standard_artifacts.human_output
    human_output = _safe_read(svc, list_resp.standard_artifacts.get("human_output"))

    # diff: from output_artifacts — role=code_diff or path ends with .diff
    diff_ref = _find_artifact_by_role(list_resp.artifacts, "code_diff", ".diff")
    if diff_ref is None:
        diff_ref = _find_artifact_by_role(list_resp.artifacts, "diff", ".diff")
    diff = _safe_read(svc, diff_ref.path if diff_ref else None)

    # review_report: role=review_report or name/path contains review_report or review + .md
    review_ref = _find_artifact_by_role(list_resp.artifacts, "review_report")
    if review_ref is None:
        review_ref = _find_artifact_by_name(list_resp.artifacts, "review_report")
    if review_ref is None:
        for a in list_resp.artifacts:
            name_lower = a.name.lower()
            path_lower = a.path.lower()
            if "review" in name_lower or "review" in path_lower:
                if path_lower.endswith(".md"):
                    review_ref = a
                    break
    review_report = _safe_read(svc, review_ref.path if review_ref else None)

    return ReviewAssetsResponse(
        pipeline_id=pipeline_id,
        stage_id=stage_id,
        human_output=human_output,
        diff=diff,
        review_report=review_report,
        artifacts=list_resp.artifacts,
    )
