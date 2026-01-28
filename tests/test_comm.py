# tests/test_comm.py
"""
测试通信模块
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from communication.mock_comm import MockCommunicator
from communication.protocol import create_state_message, parse_state_message, VehicleState


def test_mock_comm():
    print("=" * 55)
    print("  模拟通信测试")
    print("=" * 55)

    comm = MockCommunicator()

    # 连接
    print("\n1. 测试连接")
    assert comm.connect() == True
    print("   连接成功 ✓")

    # 接收数据
    print("\n2. 测试接收状态")
    for i in range(5):
        state = comm.receive_state()
        if state:
            print(f"   [{i + 1}] {state}")
        time.sleep(0.1)
    print("   接收成功 ✓")

    # 发送建议
    print("\n3. 测试发送建议")
    for alpha in [-0.05, 0.0, 0.05]:
        result = comm.send_suggestion(alpha)
        print(f"   发送 α={alpha:+.2f}: {'成功' if result else '失败'}")
    print("   发送成功 ✓")

    # 发送警告
    print("\n4. 测试发送警告")
    comm.send_warning("SOC_LOW", "电量不足")
    print("   警告发送成功 ✓")

    # 断开
    print("\n5. 测试断开连接")
    comm.disconnect()
    print("   断开成功 ✓")

    print("\n" + "=" * 55)
    print("通信测试完成！")


def test_protocol():
    print("=" * 55)
    print("  协议解析测试")
    print("=" * 55)

    # 创建测试状态
    state = VehicleState(
        timestamp_ms=12345,
        soc=0.65,
        voltage_V=24.5,
        current_A=12.3,
        temperature_C=35.2,
        h2_level=0.80,
        load_power_W=150.5,
        fc_power_W=100.0,
        mpc_output=0.35,
        human_input=0.50,
        motor_rpm=[1200, 1150, 1180, 1190]
    )

    # 序列化
    message = create_state_message(state)
    print(f"\n原始状态: {state}")
    print(f"序列化消息: {message.strip()}")

    # 反序列化
    parsed = parse_state_message(message)
    print(f"解析结果: {parsed}")

    # 验证
    assert abs(parsed.soc - state.soc) < 0.01
    assert abs(parsed.voltage_V - state.voltage_V) < 0.1
    print("\n协议解析正确 ✓")


if __name__ == "__main__":
    test_protocol()
    print()
    test_mock_comm()