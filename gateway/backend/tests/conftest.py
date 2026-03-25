"""
pytest 共享 fixtures：内存 SQLite（aiosqlite）+ httpx AsyncClient。
所有 fixture 和测试均为 async，通过 anyio 驱动。
"""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# 固定只使用 asyncio 后端（aiosqlite 不支持 trio）
@pytest.fixture(params=["asyncio"])
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def async_engine():
    """每个测试函数独立的内存 async 引擎。"""
    eng = create_async_engine(TEST_DATABASE_URL, poolclass=StaticPool)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture
async def db_session(async_engine):
    """产生一个绑定到内存引擎的 AsyncSession。"""
    Session = async_sessionmaker(async_engine, expire_on_commit=False)
    async with Session() as session:
        yield session


@pytest.fixture
async def client(db_session):
    """覆盖 get_db 依赖，TestClient 使用内存数据库。"""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()
