"""
从 .env 加载运行时配置。
"""
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./inference.db")
SCHEDULER_URL: str = os.getenv("SCHEDULER_URL", "http://localhost:8002")
