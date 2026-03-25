#!/usr/bin/env python3
"""
统一数据库初始化脚本。

用法
----
# 初始化全部模块
python scripts/init_db.py

# 仅初始化指定模块
python scripts/init_db.py gateway
python scripts/init_db.py scheduler
python scripts/init_db.py monitor

每个模块独立一个 SQLite 文件，路径通过对应模块目录下的 .env 控制：
  gateway/backend/.env   → DATABASE_URL
  scheduler/.env         → SCHEDULER_DATABASE_URL
  monitor/.env           → MONITOR_DATABASE_URL
"""
import asyncio
import sys
from pathlib import Path

# 将各模块加入 sys.path，使 import 正常工作
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "gateway" / "backend"))
sys.path.insert(0, str(ROOT / "scheduler"))
sys.path.insert(0, str(ROOT / "monitor"))


# ---------------------------------------------------------------------------
# 各模块初始化函数
# ---------------------------------------------------------------------------

async def init_gateway():
    import importlib, os
    os.chdir(ROOT / "gateway" / "backend")          # 让 .env 相对路径生效
    from dotenv import load_dotenv
    load_dotenv(ROOT / "gateway" / "backend" / ".env")

    # 重新导入以拿到正确的 DATABASE_URL
    import app.config as cfg
    importlib.reload(cfg)
    import app.database as db_mod
    importlib.reload(db_mod)
    import app.models  # noqa: F401 — 触发 Base 注册

    from app.database import Base, engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print(f"  [gateway]   ✓  {cfg.DATABASE_URL}")


async def init_scheduler():
    import os
    os.chdir(ROOT / "scheduler")
    from dotenv import load_dotenv
    load_dotenv(ROOT / "scheduler" / ".env") if (ROOT / "scheduler" / ".env").exists() else None

    from scheduler.app.database import engine
    from scheduler.app.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

    import os
    db_url = os.getenv("SCHEDULER_DATABASE_URL", "sqlite+aiosqlite:///./scheduler.db")
    print(f"  [scheduler] ✓  {db_url}")


async def init_monitor():
    import os
    os.chdir(ROOT / "monitor")
    from dotenv import load_dotenv
    load_dotenv(ROOT / "monitor" / ".env") if (ROOT / "monitor" / ".env").exists() else None

    from monitor.app.database import engine
    from monitor.app.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

    db_url = os.getenv("MONITOR_DATABASE_URL", "sqlite+aiosqlite:///./monitor.db")
    print(f"  [monitor]   ✓  {db_url}")


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

MODULES = {
    "gateway": init_gateway,
    "scheduler": init_scheduler,
    "monitor": init_monitor,
}


async def main(targets: list[str]):
    print("初始化数据库表结构...\n")
    for name in targets:
        try:
            await MODULES[name]()
        except Exception as exc:
            print(f"  [{name}] ✗  {exc}")
    print("\n完成。")


if __name__ == "__main__":
    targets = sys.argv[1:] if len(sys.argv) > 1 else list(MODULES.keys())
    unknown = [t for t in targets if t not in MODULES]
    if unknown:
        print(f"未知模块：{unknown}，可选：{list(MODULES.keys())}")
        sys.exit(1)
    asyncio.run(main(targets))
