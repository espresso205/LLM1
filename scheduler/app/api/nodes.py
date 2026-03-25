"""
节点管理路由：

  POST /api/v1/nodes                       注册节点
  POST /api/v1/nodes/{node_id}/heartbeat   心跳上报
  GET  /api/v1/select_node                 选择最优节点
  GET  /api/v1/nodes                       节点列表
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import HeartbeatRequest, NodeRegisterRequest, NodeResponse, SelectNodeResponse
from app import store

router = APIRouter(tags=["nodes"])


@router.post(
    "/nodes",
    response_model=NodeResponse,
    summary="注册推理节点",
    description="注册新节点，若 node_id 已存在则更新地址并重置为 healthy。",
)
async def register_node(
    body: NodeRegisterRequest, db: AsyncSession = Depends(get_db)
):
    node = await store.register_or_update(db, body.node_id, body.url, body.api_key)
    return NodeResponse.model_validate(node)


@router.post(
    "/nodes/{node_id}/heartbeat",
    response_model=NodeResponse,
    summary="心跳上报",
    description="节点上报当前连接数和状态，刷新 last_heartbeat。",
    responses={404: {"description": "节点不存在"}},
)
async def heartbeat(
    node_id: str, body: HeartbeatRequest, db: AsyncSession = Depends(get_db)
):
    node = await store.update_heartbeat(
        db, node_id, body.current_connections, body.status
    )
    if node is None:
        raise HTTPException(status_code=404, detail=f"节点 {node_id!r} 不存在，请先注册")
    return NodeResponse.model_validate(node)


@router.get(
    "/select_node",
    response_model=SelectNodeResponse,
    summary="选择最优节点（最少连接数）",
    description="返回当前 healthy 且连接数最少的节点，供网关转发推理请求。",
    responses={503: {"description": "暂无可用节点"}},
)
async def select_node(db: AsyncSession = Depends(get_db)):
    node = await store.select_best_node(db)
    if node is None:
        raise HTTPException(status_code=503, detail="暂无可用推理节点，请稍后重试")
    return SelectNodeResponse(node_id=node.node_id, url=node.url)


@router.get(
    "/nodes",
    response_model=list[NodeResponse],
    summary="获取全部节点列表",
    description="返回所有节点的详细状态（含离线节点），用于仪表盘展示。",
)
async def list_nodes(db: AsyncSession = Depends(get_db)):
    nodes = await store.list_nodes(db)
    return [NodeResponse.model_validate(n) for n in nodes]
