# tests/test_health.py
"""
测试健康监测模块
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from communication.protocol import VehicleState
from modules.state_manager import StateManager
from modules.health_monitor import HealthMonitor, HealthLevel


def test_health_monitor():
    print("=" * 55)
    print("  健康监测测试")
    print("=" * 55)

    state_manager = StateManager()
    monitor = HealthMonitor(state_manager)

    # 测试用例
    test_cases = [
        ("正常状态", VehicleState(soc=0.5, voltage_V=24.0, current_A=10.0,
                                  temperature_C=30.0, h2_level=0.5)),
        ("低SOC警告", VehicleState(soc=0.20, voltage_V=23.0, current_A=10.0,
                                   temperature_C=30.0, h2_level=0.5)),
        ("严重低SOC", VehicleState(soc=0.10, voltage_V=21.0, current_A=10.0,
                                   temperature_C=30.0, h2_level=0.5)),
        ("高温警告", VehicleState(soc=0.5, voltage_V=24.0, current_A=10.0,
                                  temperature_C=50.0, h2_level=0.5)),
        ("严重高温", VehicleState(soc=0.5, voltage_V=24.0, current_A=10.0,
                                  temperature_C=65.0, h2_level=0.5)),
        ("氢气不足", VehicleState(soc=0.5, voltage_V=24.0, current_A=10.0,
                                  temperature_C=30.0, h2_level=0.08)),
        ("多重问题", VehicleState(soc=0.12, voltage_V=19.0, current_A=55.0,
                                  temperature_C=62.0, h2_level=0.05)),
    ]

    for name, state in test_cases:
        print(f"\n测试: {name}")
        print(f"  状态: SOC={state.soc:.0%}, V={state.voltage_V}V, "
              f"T={state.temperature_C}°C, H2={state.h2_level:.0%}")

        state_manager.update(state)
        monitor.update_state_time()
        issues = monitor.check()

        if issues:
            for issue in issues:
                level_icon = {
                    HealthLevel.OK: "✓",
                    HealthLevel.INFO: "ℹ",
                    HealthLevel.WARNING: "⚠",
                    HealthLevel.CRITICAL: "✗"
                }[issue.level]
                print(f"  {level_icon} [{issue.code}] {issue.message}")
        else:
            print("  ✓ 一切正常")

    print("\n" + "=" * 55)
    print("健康监测测试完成！")


if __name__ == "__main__":
    test_health_monitor()