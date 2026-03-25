#!/usr/bin/env python3
"""
用法：
  python run.py                    # 使用 .env
  python run.py --env .env.node1   # 节点 1
  python run.py --env .env.node2   # 节点 2
"""
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument("--env", default=".env", help="指定要加载的环境变量文件")
args = parser.parse_args()

# 优先加载指定文件，override=True 确保覆盖已有环境变量
from dotenv import load_dotenv
load_dotenv(args.env, override=True)

import uvicorn

port = int(os.getenv("NODE_PORT", "8001"))
uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
