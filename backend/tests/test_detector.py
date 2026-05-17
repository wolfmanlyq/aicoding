"""异常检测的验证用例。直接运行：python3 backend/tests/test_detector.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.datasource import load_scenarios
from backend.app.detector import detect


def test_detects_payment_gateway_breach():
    """支付网关业务成功率跌破阈值，应被检测为 P1。"""
    scenario = next(
        s for s in load_scenarios() if s["name"] == "scenario_payment_gateway"
    )
    anomalies = detect(scenario["metrics"])
    gateway = next(a for a in anomalies if a.object == "支付网关")
    assert gateway.severity == "P1", gateway.severity
    assert gateway.current_value == 78.0
    assert gateway.detected_at == "2026-05-17T14:01:00"


def test_healthy_series_not_flagged():
    """账户查询业务成功率正常，不应产生异常。"""
    scenario = next(
        s for s in load_scenarios() if s["name"] == "scenario_payment_gateway"
    )
    anomalies = detect(scenario["metrics"])
    assert all(a.object != "账户查询" for a in anomalies)


if __name__ == "__main__":
    test_detects_payment_gateway_breach()
    test_healthy_series_not_flagged()
    print("detector 测试通过：检测到支付网关 P1 异常，账户查询未误报。")
