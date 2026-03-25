"""
推理节点配置：从环境变量读取（支持 .env 文件）。
"""
import os
from dotenv import load_dotenv

load_dotenv(override=False)  # run.py 已用 override=True 加载指定文件，此处不覆盖

# 本节点身份
NODE_ID: str = os.getenv("NODE_ID", "deepseek-1")
NODE_PORT: int = int(os.getenv("NODE_PORT", "8001"))
NODE_URL: str = os.getenv("NODE_URL", f"http://localhost:{NODE_PORT}")

# 调度器地址
SCHEDULER_URL: str = os.getenv("SCHEDULER_URL", "http://localhost:8002")

# DeepSeek API
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 心跳间隔（秒）
HEARTBEAT_INTERVAL: int = int(os.getenv("HEARTBEAT_INTERVAL", "5"))
