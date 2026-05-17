"""阶段 0 骨架：数据源读取。

当前从 data/scenario_* 目录读取样例数据，代替真实的 ES 查询。
后续按需求 FR-1.1 加厚为 ES 查询适配层。
"""
from __future__ import annotations

import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DATA_DIR = _REPO_ROOT / "data"


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_scenarios() -> list[dict]:
    """加载所有故障场景。每个场景含业务指标与故障详情样例。"""
    scenarios: list[dict] = []
    for scenario_dir in sorted(_DATA_DIR.glob("scenario_*")):
        metrics_file = scenario_dir / "business_metrics.json"
        fixture_file = scenario_dir / "incident_fixture.json"
        if not (metrics_file.exists() and fixture_file.exists()):
            continue
        scenarios.append(
            {
                "name": scenario_dir.name,
                "metrics": _load_json(metrics_file),
                "fixture": _load_json(fixture_file),
            }
        )
    return scenarios
