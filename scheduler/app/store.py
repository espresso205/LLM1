"""
调度器存储层：节点 CRUD + 调度策略（最少连接数）。
"""
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import NodeRecord


async def register_or_update(
    db: AsyncSession, node_id: str, url: str, api_key: str
) -> NodeRecord:
    """注册新节点；若已存在则更新 url 和 api_key，重置为 healthy。"""
    result = await db.execute(
        select(NodeRecord).where(NodeRecord.node_id == node_id)
    )
    node = result.scalar_one_or_none()
    if node is None:
        node = NodeRecord(
            node_id=node_id,
            url=url,
            api_key=api_key,
            current_connections=0,
            status="healthy",
            last_heartbeat=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        db.add(node)
    else:
        node.url = url
        node.api_key = api_key
        node.status = "healthy"
        node.last_heartbeat = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(node)
    return node


async def update_heartbeat(
    db: AsyncSession, node_id: str, current_connections: int, status: str
) -> NodeRecord | None:
    """更新心跳时间和连接数。节点不存在时返回 None。"""
    result = await db.execute(
        select(NodeRecord).where(NodeRecord.node_id == node_id)
    )
    node = result.scalar_one_or_none()
    if node is None:
        return None
    node.current_connections = current_connections
    node.status = status
    node.last_heartbeat = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(node)
    return node


async def select_best_node(db: AsyncSession) -> NodeRecord | None:
    """
    最少连接数策略：选择 healthy 且 current_connections 最小的节点。
    若多个节点连接数相同，随机选一个。
    """
    result = await db.execute(
        select(NodeRecord).where(NodeRecord.status == "healthy")
    )
    nodes = result.scalars().all()
    if not nodes:
        return None
    min_conns = min(n.current_connections for n in nodes)
    candidates = [n for n in nodes if n.current_connections == min_conns]
    return random.choice(candidates)


async def list_nodes(db: AsyncSession) -> list[NodeRecord]:
    """返回全部节点，按创建时间升序。"""
    result = await db.execute(
        select(NodeRecord).order_by(NodeRecord.created_at)
    )
    return list(result.scalars().all())


async def mark_offline_stale(db: AsyncSession, threshold_seconds: int = 35) -> int:
    """
    将心跳超时超过 threshold_seconds 秒的节点标记为 offline。
    返回被标记的节点数。
    """
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=threshold_seconds)
    result = await db.execute(
        select(NodeRecord).where(
            NodeRecord.status == "healthy",
            NodeRecord.last_heartbeat < cutoff,
        )
    )
    stale = result.scalars().all()
    for node in stale:
        node.status = "offline"
    if stale:
        await db.commit()
    return len(stale)
