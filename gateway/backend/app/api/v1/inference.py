"""
推理相关路由（全部 async）：

  POST /api/v1/inference                    提交推理
  GET  /api/v1/history                      历史列表（分页 + 筛选）
  GET  /api/v1/history/{request_id}         单条详情
  POST /api/v1/inference/{request_id}/retry 重试历史请求
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import store
from app.config import SCHEDULER_URL
from app.database import get_db
from app.models import RequestRecord
from app.schemas import (
    HistoryDetail,
    HistoryItem,
    HistoryResponse,
    InferenceRequest,
    InferenceResponse,
)

router = APIRouter(tags=["inference"])


# ---------------------------------------------------------------------------
# POST /api/v1/inference
# ---------------------------------------------------------------------------

@router.post(
    "/inference",
    response_model=InferenceResponse,
    summary="提交推理请求",
    description="向调度器请求最优节点，将推理任务转发给推理节点，结果写入数据库后返回。",
)
async def submit_inference(
    body: InferenceRequest, db: AsyncSession = Depends(get_db)
):
    request_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)

    status = "failed"
    result = ""
    duration_ms = 0

    try:
        scheduler_result = await _call_scheduler(
            body.prompt, body.max_tokens, body.temperature
        )
        result = scheduler_result["result"]
        duration_ms = scheduler_result["duration_ms"]
        status = "success"
    except HTTPException:
        raise
    except Exception as exc:
        result = f"推理失败: {exc}"

    record = RequestRecord(
        request_id=request_id,
        prompt=body.prompt,
        max_tokens=body.max_tokens,
        temperature=body.temperature,
        result=result,
        status=status,
        created_at=created_at,
        duration_ms=duration_ms,
    )
    await store.save(db, record)

    if status == "failed":
        raise HTTPException(status_code=502, detail=result)

    return InferenceResponse(
        request_id=request_id,
        result=result,
        status=status,
        created_at=created_at,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/history
# ---------------------------------------------------------------------------

@router.get(
    "/history",
    response_model=HistoryResponse,
    summary="获取历史记录列表",
    description="支持分页（limit/offset）与状态筛选（success/failed），按创建时间倒序。",
)
async def get_history(
    limit: int = Query(20, ge=1, le=100, description="每页条数"),
    offset: int = Query(0, ge=0, description="跳过条数"),
    status: Optional[str] = Query(None, description="状态筛选：success / failed"),
    db: AsyncSession = Depends(get_db),
):
    records, total = await store.list_records(
        db, limit=limit, offset=offset, status=status
    )
    items = [
        HistoryItem(
            request_id=r.request_id,
            prompt_preview=r.prompt[:80] + ("…" if len(r.prompt) > 80 else ""),
            status=r.status,
            created_at=r.created_at,
        )
        for r in records
    ]
    return HistoryResponse(items=items, total=total)


# ---------------------------------------------------------------------------
# GET /api/v1/history/{request_id}
# ---------------------------------------------------------------------------

@router.get(
    "/history/{request_id}",
    response_model=HistoryDetail,
    summary="获取单条推理详情",
    description="返回完整 prompt、result、耗时及参数配置。",
    responses={404: {"description": "记录不存在"}},
)
async def get_history_detail(
    request_id: str, db: AsyncSession = Depends(get_db)
):
    record = await store.get_by_request_id(db, request_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"记录 {request_id!r} 不存在")
    return HistoryDetail.model_validate(record)


# ---------------------------------------------------------------------------
# POST /api/v1/inference/{request_id}/retry
# ---------------------------------------------------------------------------

@router.post(
    "/inference/{request_id}/retry",
    response_model=InferenceResponse,
    summary="重试推理请求",
    description="读取原请求参数，重新提交推理并生成新的 request_id。",
    responses={404: {"description": "原记录不存在"}},
)
async def retry_inference(
    request_id: str, db: AsyncSession = Depends(get_db)
):
    original = await store.get_by_request_id(db, request_id)
    if original is None:
        raise HTTPException(status_code=404, detail=f"原记录 {request_id!r} 不存在")

    new_request_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)

    status = "failed"
    result = ""
    duration_ms = 0

    try:
        scheduler_result = await _call_scheduler(
            original.prompt, original.max_tokens, original.temperature
        )
        result = scheduler_result["result"]
        duration_ms = scheduler_result["duration_ms"]
        status = "success"
    except HTTPException:
        raise
    except Exception as exc:
        result = f"推理失败: {exc}"

    record = RequestRecord(
        request_id=new_request_id,
        prompt=original.prompt,
        max_tokens=original.max_tokens,
        temperature=original.temperature,
        result=result,
        status=status,
        created_at=created_at,
        duration_ms=duration_ms,
    )
    await store.save(db, record)

    if status == "failed":
        raise HTTPException(status_code=502, detail=result)

    return InferenceResponse(
        request_id=new_request_id,
        result=result,
        status=status,
        created_at=created_at,
    )


# ---------------------------------------------------------------------------
# 调度器交互：选节点 → 转发推理
# ---------------------------------------------------------------------------

async def _call_scheduler(
    prompt: str, max_tokens: int, temperature: float
) -> dict:
    """
    1. 向调度器请求最优节点（GET /api/v1/select_node）
    2. 将推理请求转发给选中节点（POST {node_url}/api/v1/inference）
    3. 如果节点调用失败，最多重试 1 次（重新向调度器选节点）
    4. 返回 {result, duration_ms}
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        last_error: str = ""
        tried_nodes: set[str] = set()

        for attempt in range(2):  # 最多尝试 2 次
            # Step 1: 从调度器选节点
            try:
                sel_resp = await client.get(f"{SCHEDULER_URL}/api/v1/select_node")
                sel_resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 503:
                    raise HTTPException(status_code=503, detail="暂无可用推理节点，请稍后重试")
                raise HTTPException(
                    status_code=502,
                    detail=f"调度器错误 {exc.response.status_code}: {exc.response.text[:200]}",
                )
            except httpx.RequestError as exc:
                raise HTTPException(status_code=503, detail=f"无法连接调度器: {exc}")

            node = sel_resp.json()
            node_id: str = node["node_id"]
            node_url: str = node["url"]

            # 如果是重试且选到同一个节点，直接放弃
            if attempt > 0 and node_id in tried_nodes:
                break

            tried_nodes.add(node_id)

            # Step 2: 转发推理请求
            try:
                infer_resp = await client.post(
                    f"{node_url}/api/v1/inference",
                    json={
                        "prompt": prompt,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                )
                infer_resp.raise_for_status()
                data = infer_resp.json()
                return {"result": data["result"], "duration_ms": data["duration_ms"]}
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                last_error = (
                    f"节点 {node_id} 错误: "
                    f"{exc.response.text[:200]}"
                    if isinstance(exc, httpx.HTTPStatusError)
                    else f"节点 {node_id} 连接失败: {exc}"
                )
                # 继续下一次重试

        raise HTTPException(status_code=502, detail=last_error or "推理节点调用失败")
