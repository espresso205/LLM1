"""
推理节点 FastAPI 主程序。

功能：
  - POST /api/v1/inference  接收推理请求，调用 DeepSeek API 并返回结果
  - GET  /api/v1/status     节点状态页（HTML）
  - GET  /health            健康检查（JSON，供调度器探测）
  - 启动时向调度器注册，后台每 5 秒发送心跳（包含当前连接数）
  - 请求前连接数 +1，请求处理完毕后 -1
"""
import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.config import (
    DEEPSEEK_API_KEY,
    HEARTBEAT_INTERVAL,
    NODE_ID,
    NODE_PORT,
    NODE_URL,
    SCHEDULER_URL,
)
from app.inference import run_inference

logger = logging.getLogger("inference_node")

# 节点运行时状态
_current_connections: int = 0
_last_heartbeat_time: str = "尚未上报"
_start_time: str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
_total_requests: int = 0
_failed_requests: int = 0


# ---------------------------------------------------------------------------
# 注册 + 心跳
# ---------------------------------------------------------------------------

async def _register():
    """启动时向调度器注册本节点。"""
    payload = {"node_id": NODE_ID, "url": NODE_URL, "api_key": DEEPSEEK_API_KEY}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{SCHEDULER_URL}/api/v1/nodes", json=payload)
        resp.raise_for_status()
    logger.info(f"[{NODE_ID}] 已注册到调度器 {SCHEDULER_URL}")


async def _heartbeat_loop():
    """每 HEARTBEAT_INTERVAL 秒向调度器上报心跳和连接数。"""
    global _last_heartbeat_time
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{SCHEDULER_URL}/api/v1/nodes/{NODE_ID}/heartbeat",
                    json={"current_connections": _current_connections, "status": "healthy"},
                )
                resp.raise_for_status()
            _last_heartbeat_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception as exc:
            logger.warning(f"[{NODE_ID}] 心跳失败: {exc}")


# ---------------------------------------------------------------------------
# 生命周期
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        await _register()
    except Exception as exc:
        logger.warning(f"[{NODE_ID}] 注册失败（调度器可能未启动）: {exc}")
    task = asyncio.create_task(_heartbeat_loop())
    yield
    task.cancel()


# ---------------------------------------------------------------------------
# 应用实例
# ---------------------------------------------------------------------------

app = FastAPI(
    title=f"推理节点 [{NODE_ID}]",
    description="接收网关推理请求，调用 DeepSeek API 执行推理并返回结果。",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# 请求/响应 Schema
# ---------------------------------------------------------------------------

class InferenceRequest(BaseModel):
    prompt: str
    max_tokens: int = 512
    temperature: float = 0.7


class InferenceResponse(BaseModel):
    request_id: str
    result: str
    duration_ms: int
    status: str


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------

@app.post(
    "/api/v1/inference",
    response_model=InferenceResponse,
    summary="执行推理",
    description="接收 prompt 及参数，调用 DeepSeek API 返回生成结果。",
)
async def inference(body: InferenceRequest):
    global _current_connections, _total_requests, _failed_requests
    request_id = str(uuid.uuid4())
    _current_connections += 1
    _total_requests += 1
    try:
        out = await run_inference(body.prompt, body.max_tokens, body.temperature)
        return InferenceResponse(
            request_id=request_id,
            result=out["result"],
            duration_ms=out["duration_ms"],
            status="success",
        )
    except httpx.HTTPStatusError as exc:
        _failed_requests += 1
        raise HTTPException(
            status_code=502,
            detail=f"DeepSeek API 错误 {exc.response.status_code}: {exc.response.text[:300]}",
        )
    except Exception as exc:
        _failed_requests += 1
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        _current_connections -= 1


@app.get("/health", summary="健康检查（JSON）")
async def health():
    return {
        "node_id": NODE_ID,
        "status": "healthy",
        "current_connections": _current_connections,
    }


# ---------------------------------------------------------------------------
# 节点状态页
# ---------------------------------------------------------------------------

STATUS_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="5">
<title>节点状态 - {node_id}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         background: #f0f2f5; color: #333; }}
  header {{ background: #0f3460; color: #fff; padding: 16px 32px; }}
  header h1 {{ font-size: 20px; }}
  main {{ max-width: 700px; margin: 32px auto; padding: 0 24px; }}
  .card {{ background: #fff; border-radius: 10px; padding: 24px;
           box-shadow: 0 2px 8px rgba(0,0,0,.08); margin-bottom: 20px; }}
  .card h2 {{ font-size: 15px; color: #888; margin-bottom: 16px; text-transform: uppercase;
              letter-spacing: .05em; }}
  table {{ width: 100%; border-collapse: collapse; }}
  td {{ padding: 10px 0; border-bottom: 1px solid #f0f0f0; font-size: 14px; }}
  td:first-child {{ color: #888; width: 45%; }}
  tr:last-child td {{ border-bottom: none; }}
  .badge {{ display: inline-block; padding: 3px 12px; border-radius: 99px;
            background: #dcfce7; color: #16a34a; font-size: 13px; font-weight: 600; }}
  .note {{ font-size: 12px; color: #aaa; margin-top: 8px; text-align: right; }}
</style>
</head>
<body>
<header><h1>🖥 推理节点状态</h1></header>
<main>
  <div class="card">
    <h2>节点信息</h2>
    <table>
      <tr><td>节点 ID</td><td><b>{node_id}</b></td></tr>
      <tr><td>节点地址</td><td>{node_url}</td></tr>
      <tr><td>调度器地址</td><td>{scheduler_url}</td></tr>
      <tr><td>启动时间</td><td>{start_time}</td></tr>
      <tr><td>运行状态</td><td><span class="badge">healthy</span></td></tr>
    </table>
  </div>
  <div class="card">
    <h2>实时指标</h2>
    <table>
      <tr><td>当前并发连接数</td><td><b>{current_connections}</b></td></tr>
      <tr><td>累计请求数</td><td>{total_requests}</td></tr>
      <tr><td>失败请求数</td><td>{failed_requests}</td></tr>
      <tr><td>最后心跳时间</td><td>{last_heartbeat}</td></tr>
    </table>
  </div>
  <p class="note">每 5 秒自动刷新</p>
</main>
</body>
</html>"""


@app.get("/api/v1/status", response_class=HTMLResponse, summary="节点状态页")
async def status():
    return STATUS_HTML.format(
        node_id=NODE_ID,
        node_url=NODE_URL,
        scheduler_url=SCHEDULER_URL,
        start_time=_start_time,
        current_connections=_current_connections,
        total_requests=_total_requests,
        failed_requests=_failed_requests,
        last_heartbeat=_last_heartbeat_time,
    )
