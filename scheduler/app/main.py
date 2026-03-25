"""
调度器 FastAPI 主程序。
  - 端口 8002
  - GET /dashboard  ：节点状态仪表盘（HTML）
  - /api/v1/...     ：节点管理 API
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.database import engine, async_session_factory
from app.models import Base
from app.api.nodes import router as nodes_router
from app import store

logger = logging.getLogger("scheduler")


# ---------------------------------------------------------------------------
# 后台任务：定期扫描离线节点
# ---------------------------------------------------------------------------

async def _offline_watcher():
    """每 15 秒检查一次：连续 3 次未收到心跳（约 35s）的节点标为 offline。"""
    while True:
        await asyncio.sleep(15)
        try:
            async with async_session_factory() as db:
                count = await store.mark_offline_stale(db, threshold_seconds=35)
                if count:
                    logger.info(f"[watcher] 已将 {count} 个超时节点标记为 offline")
        except Exception as exc:
            logger.error(f"[watcher] 检查失败: {exc}")


# ---------------------------------------------------------------------------
# 生命周期
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    task = asyncio.create_task(_offline_watcher())
    yield
    task.cancel()
    await engine.dispose()


# ---------------------------------------------------------------------------
# 应用实例
# ---------------------------------------------------------------------------

app = FastAPI(
    title="推理调度器",
    description="管理推理节点注册、心跳、负载均衡（最少连接数策略）",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(nodes_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# 仪表盘（纯 HTML + JS，无模板依赖）
# ---------------------------------------------------------------------------

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>推理节点仪表盘</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         background: #f0f2f5; color: #333; }
  header { background: #1a1a2e; color: #fff; padding: 16px 32px;
           display: flex; align-items: center; justify-content: space-between; }
  header h1 { font-size: 20px; font-weight: 600; }
  #refresh-btn { background: #4361ee; color: #fff; border: none; padding: 8px 18px;
                 border-radius: 6px; cursor: pointer; font-size: 14px; }
  #refresh-btn:hover { background: #3a56d4; }
  main { max-width: 1100px; margin: 32px auto; padding: 0 24px; }
  .summary { display: flex; gap: 16px; margin-bottom: 24px; }
  .card { background: #fff; border-radius: 10px; padding: 20px 28px;
          box-shadow: 0 2px 8px rgba(0,0,0,.08); flex: 1; }
  .card .num { font-size: 36px; font-weight: 700; margin-bottom: 4px; }
  .card .label { font-size: 13px; color: #888; }
  .num.green { color: #22c55e; }
  .num.red   { color: #ef4444; }
  .num.blue  { color: #3b82f6; }
  table { width: 100%; border-collapse: collapse; background: #fff;
          border-radius: 10px; overflow: hidden;
          box-shadow: 0 2px 8px rgba(0,0,0,.08); }
  th { background: #1a1a2e; color: #fff; padding: 12px 16px;
       text-align: left; font-size: 13px; font-weight: 500; }
  td { padding: 12px 16px; border-bottom: 1px solid #f0f0f0; font-size: 14px; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: #fafafa; }
  .badge { display: inline-block; padding: 3px 10px; border-radius: 99px;
           font-size: 12px; font-weight: 600; }
  .badge.healthy { background: #dcfce7; color: #16a34a; }
  .badge.offline { background: #fee2e2; color: #dc2626; }
  #last-update { font-size: 12px; color: #aaa; margin-top: 12px; text-align: right; }
</style>
</head>
<body>
<header>
  <h1>🖥 推理节点仪表盘</h1>
  <button id="refresh-btn" onclick="loadNodes()">刷新</button>
</header>
<main>
  <div class="summary">
    <div class="card"><div class="num blue" id="total">—</div><div class="label">节点总数</div></div>
    <div class="card"><div class="num green" id="healthy">—</div><div class="label">在线节点</div></div>
    <div class="card"><div class="num red" id="offline">—</div><div class="label">离线节点</div></div>
    <div class="card"><div class="num blue" id="conns">—</div><div class="label">总并发连接</div></div>
  </div>
  <table>
    <thead>
      <tr>
        <th>节点 ID</th><th>地址</th><th>状态</th>
        <th>并发连接</th><th>最后心跳</th><th>注册时间</th>
      </tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>
  <div id="last-update"></div>
</main>
<script>
async function loadNodes() {
  try {
    const res = await fetch('/api/v1/nodes');
    const nodes = await res.json();
    const tbody = document.getElementById('tbody');
    tbody.innerHTML = '';
    let healthy = 0, offline = 0, conns = 0;
    nodes.forEach(n => {
      if (n.status === 'healthy') healthy++; else offline++;
      conns += n.current_connections;
      const hb = new Date(n.last_heartbeat).toLocaleString('zh-CN');
      const ca = new Date(n.created_at).toLocaleString('zh-CN');
      tbody.innerHTML += `<tr>
        <td><b>${n.node_id}</b></td>
        <td>${n.url}</td>
        <td><span class="badge ${n.status}">${n.status === 'healthy' ? '在线' : '离线'}</span></td>
        <td>${n.current_connections}</td>
        <td>${hb}</td>
        <td>${ca}</td>
      </tr>`;
    });
    document.getElementById('total').textContent = nodes.length;
    document.getElementById('healthy').textContent = healthy;
    document.getElementById('offline').textContent = offline;
    document.getElementById('conns').textContent = conns;
    document.getElementById('last-update').textContent =
      '最后更新：' + new Date().toLocaleTimeString('zh-CN');
  } catch(e) {
    console.error(e);
  }
}
loadNodes();
setInterval(loadNodes, 10000);
</script>
</body>
</html>"""


@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard():
    return DASHBOARD_HTML
