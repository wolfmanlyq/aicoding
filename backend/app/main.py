"""阶段 0 骨架：FastAPI 应用。

端到端链路：样例业务指标 → 异常检测 → 生成故障事件 → API → Web 界面。
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .datasource import load_scenarios
from .detector import detect

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WEB_DIR = _REPO_ROOT / "web"

app = FastAPI(title="业务影响分析与根因定位监控系统 — 阶段0骨架")


def build_incidents() -> dict[str, dict]:
    """跑通：检测异常 → 与场景详情合并为故障事件。

    检测得到的字段（级别、检测时间、持续时长、当前值）为实时计算；
    故障详情的根因/日志/处置等为场景样例（骨架阶段的 dumb baseline）。
    """
    incidents: dict[str, dict] = {}
    for scenario in load_scenarios():
        fixture = scenario["fixture"]
        anomalies = detect(scenario["metrics"])
        match = next(
            (a for a in anomalies if a.object == fixture["scenario_object"]),
            None,
        )
        if match is None:
            continue

        detail = dict(fixture)
        detail.update(
            severity=match.severity,
            status="进行中",
            detected_at=match.detected_at,
            duration_min=match.duration_min,
            baseline_value=match.baseline_value,
            current_value=match.current_value,
            drop=match.drop,
            metric=match.metric,
        )
        incidents[detail["id"]] = detail
    return incidents


@app.get("/api/incidents")
def list_incidents() -> list[dict]:
    """故障大盘：进行中故障列表。"""
    summaries = []
    severity_order = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}
    for inc in build_incidents().values():
        summaries.append(
            {
                "id": inc["id"],
                "title": inc["title"],
                "severity": inc["severity"],
                "status": inc["status"],
                "duration_min": inc["duration_min"],
                "business": inc["affected_business_short"],
                "conclusion": inc["conclusion"],
                "root_cause": inc["root_cause"],
                "suggested_action": inc["suggested_action"],
            }
        )
    summaries.sort(key=lambda s: severity_order.get(s["severity"], 9))
    return summaries


@app.get("/api/incidents/{incident_id}")
def get_incident(incident_id: str) -> dict:
    """故障详情：三段式详情页所需的完整数据。"""
    incident = build_incidents().get(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="故障事件不存在")
    return incident


@app.get("/")
def index() -> FileResponse:
    return FileResponse(_WEB_DIR / "index.html")


app.mount("/", StaticFiles(directory=_WEB_DIR), name="web")
