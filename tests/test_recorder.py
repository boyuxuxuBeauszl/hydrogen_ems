# tests/test_recorder.py
"""
测试数据记录模块
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from communication.protocol import VehicleState
from modules.data_recorder import DataRecorder


def test_recorder():
    print("=" * 55)
    print("  数据记录测试")
    print("=" * 55)

    recorder = DataRecorder()

    print(f"\n配置:")
    print(f"  启用: {recorder.enabled}")
    print(f"  目录: {recorder.output_dir}")
    print(f"  格式: {recorder.format}")

    # 记录一些测试数据
    print("\n记录测试数据...")

    for i in range(20):
        state = VehicleState(
            timestamp_ms=i * 100,
            soc=0.5 + i * 0.01,
            voltage_V=24.0 + i * 0.1,
            current_A=10.0 + i * 0.2,
            temperature_C=30.0 + i * 0.5,
            h2_level=0.9 - i * 0.02,
            load_power_W=100 + i * 5,
            fc_power_W=50 + i * 2,
            mpc_output=0.3 + i * 0.01,
            human_input=0.0,
            motor_rpm=[1000 + i * 10, 1000 + i * 10, 1000 + i * 10, 1000 + i * 10]
        )

        recorder.record(
            state=state,
            cycle_count=i,
            dqn_alpha=0.01 * (i % 5 - 2),
            dqn_confidence=0.8 + i * 0.005,
            health_ok=True,
            health_issues=[]
        )

        time.sleep(0.05)

    recorder.flush()

    print(f"\n统计:")
    stats = recorder.stats
    for key, value in stats.items():
        print(f"  {key}: {value}")

    recorder.close()

    # 检查文件
    if os.path.exists(stats['current_file']):
        print(f"\n文件已创建: {stats['current_file']}")
        with open(stats['current_file'], 'r') as f:
            lines = f.readlines()
            print(f"文件行数: {len(lines)}")
            print(f"表头: {lines[0].strip()[:80]}...")
            print(f"首条数据: {lines[1].strip()[:80]}...")

    print("\n" + "=" * 55)
    print("数据记录测试完成！")


if __name__ == "__main__":
    test_recorder()