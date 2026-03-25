"""
调度器数据层：NodeRecord + ScheduleDecision。
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class NodeRecord(Base):
    """
    计算节点注册表。

    字段说明
    --------
    node_id             : 节点唯一标识，如 "deepseek-1"
    url                 : 节点服务地址，如 "http://localhost:8001"
    api_key             : 该节点持有的 DeepSeek API Key
    current_connections : 当前并发请求数（由节点心跳上报）
    status              : healthy | offline
    last_heartbeat      : 最近一次心跳时间（UTC）
    created_at          : 节点首次注册时间（UTC）
    """
    __tablename__ = "node_records"
    __table_args__ = (
        Index("ix_node_records_status", "status"),
        Index("ix_node_records_last_heartbeat", "last_heartbeat"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    url: Mapped[str] = mapped_column(String(256), nullable=False)
    api_key: Mapped[str] = mapped_column(String(64), nullable=False)
    current_connections: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="healthy")
    last_heartbeat: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    decisions: Mapped[list["ScheduleDecision"]] = relationship(
        back_populates="node", cascade="all, delete-orphan"
    )


class ScheduleDecision(Base):
    """
    调度决策审计记录：每次将请求分配给某节点时写入一条。
    """
    __tablename__ = "schedule_decisions"
    __table_args__ = (
        Index("ix_schedule_decisions_request_id", "request_id"),
        Index("ix_schedule_decisions_timestamp", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False)
    node_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("node_records.node_id"), nullable=False
    )
    strategy: Mapped[str] = mapped_column(String(32), nullable=False, default="least_connections")
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    node: Mapped["NodeRecord"] = relationship(back_populates="decisions")
