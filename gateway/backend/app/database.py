"""
异步 SQLAlchemy 引擎与 Session 工厂。
所有数据库操作通过 AsyncSession 完成，驱动使用 aiosqlite。
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：产生一个 AsyncSession，请求结束后自动关闭。"""
    async with async_session_factory() as session:
        yield session
