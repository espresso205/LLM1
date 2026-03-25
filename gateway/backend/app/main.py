"""
应用入口：FastAPI 实例 + CORS + lifespan（异步建表）。
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.api.v1.inference import router as inference_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # 启动时自动建表（表已存在则跳过）
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="推理网关 API",
    version="1.0.0",
    description="轻量级推理网关：提交推理、查询历史、支持重试。",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(inference_router, prefix="/api/v1")
