"""
异步数据访问层：所有 DB 操作均为 async，路由层不直接操作 ORM。
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RequestRecord


async def save(db: AsyncSession, record: RequestRecord) -> RequestRecord:
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def list_records(
    db: AsyncSession,
    limit: int = 20,
    offset: int = 0,
    status: str | None = None,
) -> tuple[list[RequestRecord], int]:
    """返回 (当页记录列表, 匹配总数)，按 created_at 倒序。"""
    stmt = select(RequestRecord)
    count_stmt = select(func.count()).select_from(RequestRecord)

    if status:
        stmt = stmt.where(RequestRecord.status == status)
        count_stmt = count_stmt.where(RequestRecord.status == status)

    total: int = (await db.execute(count_stmt)).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(RequestRecord.created_at.desc()).offset(offset).limit(limit)
        )
    ).scalars().all()

    return list(rows), total


async def get_by_request_id(
    db: AsyncSession, request_id: str
) -> RequestRecord | None:
    result = await db.execute(
        select(RequestRecord).where(RequestRecord.request_id == request_id)
    )
    return result.scalar_one_or_none()
