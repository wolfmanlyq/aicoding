"""阶段 0 骨架：最简异常检测。

读取业务指标时间序列，对"低于阈值"的指标做阈值检测，产出异常。
属 dumb baseline——后续按需求 FR-1.2 加厚为同比/环比、动态基线等。
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class Anomaly:
    object: str
    object_type: str
    business: str
    metric: str
    unit: str
    baseline_value: float
    current_value: float
    drop: float
    detected_at: str
    latest_at: str
    duration_min: int
    severity: str

    def to_dict(self) -> dict:
        return asdict(self)


def _severity(drop: float) -> str:
    """按指标跌幅粗分级。后续 FR-1.9 改为按业务重要级×受损程度×范围。"""
    if drop >= 15:
        return "P1"
    if drop >= 8:
        return "P2"
    if drop >= 3:
        return "P3"
    return "P4"


def _minutes_between(start: str, end: str) -> int:
    fmt = "%Y-%m-%dT%H:%M:%S"
    delta = datetime.strptime(end, fmt) - datetime.strptime(start, fmt)
    return int(delta.total_seconds() // 60)


def detect(metrics: dict) -> list[Anomaly]:
    """对一份业务指标数据做阈值检测，返回检测到的异常列表。"""
    anomalies: list[Anomaly] = []
    for series in metrics.get("series", []):
        if series.get("direction") != "below":
            continue
        threshold = series["threshold"]
        points = series["points"]
        if not points:
            continue

        breach = next((p for p in points if p["value"] < threshold), None)
        if breach is None:
            continue

        baseline = points[0]["value"]
        latest = points[-1]
        drop = round(baseline - latest["value"], 1)
        anomalies.append(
            Anomaly(
                object=series["object"],
                object_type=series["object_type"],
                business=series["business"],
                metric=series["metric"],
                unit=series.get("unit", ""),
                baseline_value=baseline,
                current_value=latest["value"],
                drop=drop,
                detected_at=breach["ts"],
                latest_at=latest["ts"],
                duration_min=_minutes_between(breach["ts"], latest["ts"]),
                severity=_severity(drop),
            )
        )
    return anomalies
