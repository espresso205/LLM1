"""
调度器 Pydantic 模式定义。
"""
from datetime import datetime

from pydantic import BaseModel


class NodeRegisterRequest(BaseModel):
    node_id: str
    url: str
    api_key: str


class HeartbeatRequest(BaseModel):
    current_connections: int = 0
    status: str = "healthy"


class NodeResponse(BaseModel):
    node_id: str
    url: str
    status: str
    current_connections: int
    last_heartbeat: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class SelectNodeResponse(BaseModel):
    node_id: str
    url: str
