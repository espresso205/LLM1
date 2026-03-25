"""
Pydantic 请求/响应 Schema。
"""
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 请求体
# ---------------------------------------------------------------------------

class InferenceRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="推理输入文本")
    max_tokens: int = Field(512, ge=1, le=4096, description="最大生成 token 数")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="采样温度")


# ---------------------------------------------------------------------------
# 响应体
# ---------------------------------------------------------------------------

class InferenceResponse(BaseModel):
    request_id: str
    result: str
    status: Literal["success", "failed"]
    created_at: datetime


class HistoryItem(BaseModel):
    request_id: str
    prompt_preview: str
    status: Literal["success", "failed"]
    created_at: datetime

    model_config = {"from_attributes": True}


class HistoryResponse(BaseModel):
    items: list[HistoryItem]
    total: int


class HistoryDetail(BaseModel):
    request_id: str
    prompt: str
    result: Optional[str]
    status: Literal["success", "failed"]
    duration_ms: Optional[int]
    max_tokens: int
    temperature: float
    created_at: datetime

    model_config = {"from_attributes": True}
