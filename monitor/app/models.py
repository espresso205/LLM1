"""
监控数据层：MetricPoint 时序表。
当前为纯模型定义，不包含业务逻辑。
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class MetricPoint(Base):
    """
    通用指标时序表，用于存储 QPS、延迟、错误率等监控数据。

    字段说明
    --------
    metric_name : 指标标识，如 "qps" | "latency_ms" | "error_rate" | "gpu_util"
    value       : 指标数值（浮点，兼容整数型指标）
    node_id     : 来源节点 ID；NULL 表示系统级汇总指标
    timestamp   : 采样时间（UTC），建议使用秒级精度

    典型查询模式
    -----------
    # 查询某节点最近 5 分钟的 P99 延迟
    SELECT percentile_cont(0.99) WITHIN GROUP (ORDER BY value)
    FROM metric_points
    WHERE metric_name = 'latency_ms'
      AND node_id = 'node-01'
      AND timestamp >= now() - interval '5 minutes';

    # 系统级 QPS 趋势（按分钟聚合）
    SELECT strftime('%Y-%m-%dT%H:%M:00', timestamp) AS minute,
           sum(value) AS total_qps
    FROM metric_points
    WHERE metric_name = 'qps'
    GROUP BY minute
    ORDER BY minute DESC
    LIMIT 60;
    """
    __tablename__ = "metric_points"
    __table_args__ = (
        # 时序查询的核心索引：按指标名 + 时间范围过滤
        Index("ix_metric_points_name_ts", "metric_name", "timestamp"),
        # 按节点隔离查询
        Index("ix_metric_points_node_id", "node_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    node_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
