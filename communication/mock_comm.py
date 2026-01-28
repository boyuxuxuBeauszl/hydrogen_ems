# communication/mock_comm.py
"""
模拟通信模块 - 无硬件时测试用
模拟 STM32 的行为，生成合理的传感器数据
"""

import time
import math
import random
from typing import Optional, Callable
from communication.protocol import VehicleState, parse_state_message, create_state_message


class MockSTM32:
    """
    模拟的 STM32
    生成符合物理规律的模拟数据
    """

    def __init__(self):
        # 内部状态
        self._soc = 0.65  # 初始 SOC
        self._h2_level = 0.90  # 初始氢气量
        self._temperature = 25.0  # 初始温度
        self._time_ms = 0  # 模拟时间

        # 模拟参数
        self._human_input = 0.0  # 人的输入
        self._load_base = 100.0  # 基础负载 (W)

        # 上一次的建议值
        self._last_alpha = 0.0

        # 连接状态
        self.connected = False

        print("[MockSTM32] 模拟器已创建")

    def connect(self) -> bool:
        """模拟连接"""
        self.connected = True
        self._time_ms = 0
        print("[MockSTM32] 已连接 (模拟模式)")
        return True

    def disconnect(self):
        """断开连接"""
        self.connected = False
        print("[MockSTM32] 已断开")

    def receive(self) -> Optional[VehicleState]:
        """
        接收状态数据 (模拟 STM32 发送的数据)
        """
        if not self.connected:
            return None

        # 更新模拟时间
        self._time_ms += 100  # 假设 100ms 间隔

        # 模拟人的操作 (随机变化)
        self._human_input += random.gauss(0, 0.05)
        self._human_input = max(-1.0, min(1.0, self._human_input))

        # 计算负载功率 (与人的输入相关)
        load_power = self._load_base + abs(self._human_input) * 200 + random.gauss(0, 10)
        load_power = max(0, load_power)

        # MPC 输出 (简化模型)
        mpc_output = 0.3 + self._human_input * 0.2 + random.gauss(0, 0.02)
        mpc_output = max(0, min(1, mpc_output))

        # 应用 DQN 建议后的实际功率分配
        actual_ratio = mpc_output + self._last_alpha
        actual_ratio = max(0, min(1, actual_ratio))

        # 计算燃料电池功率
        fc_power = load_power * actual_ratio

        # 更新 SOC (简化模型)
        battery_power = load_power - fc_power
        delta_soc = -battery_power * 0.0001 / 3600  # 假设 100Wh 电池
        self._soc += delta_soc
        self._soc = max(0.1, min(0.95, self._soc))

        # 更新氢气量
        if fc_power > 0:
            self._h2_level -= fc_power * 0.00001
            self._h2_level = max(0, self._h2_level)

        # 更新温度
        self._temperature += (load_power / 1000 - 0.05) + random.gauss(0, 0.1)
        self._temperature = max(20, min(70, self._temperature))

        # 电压随 SOC 变化
        voltage = 22.0 + self._soc * 4.0 + random.gauss(0, 0.1)

        # 电流
        current = load_power / voltage if voltage > 0 else 0

        # 电机转速 (随人的输入变化)
        base_rpm = 1000 + int(abs(self._human_input) * 500)
        motor_rpm = [
            base_rpm + random.randint(-50, 50),
            base_rpm + random.randint(-50, 50),
            base_rpm + random.randint(-50, 50),
            base_rpm + random.randint(-50, 50)
        ]

        # 创建状态
        state = VehicleState(
            timestamp_ms=self._time_ms,
            soc=self._soc,
            voltage_V=voltage,
            current_A=current,
            temperature_C=self._temperature,
            h2_level=self._h2_level,
            fc_power_W=fc_power,
            load_power_W=load_power,
            mpc_output=mpc_output,
            human_input=self._human_input,
            motor_rpm=motor_rpm
        )

        return state

    def send_suggestion(self, alpha: float) -> bool:
        """
        接收树莓派的建议 (模拟 STM32 收到建议)
        """
        if not self.connected:
            return False

        self._last_alpha = alpha
        return True

    def send_warning(self, code: str, message: str) -> bool:
        """发送警告"""
        if not self.connected:
            return False
        print(f"[MockSTM32] 收到警告: [{code}] {message}")
        return True


class MockCommunicator:
    """
    模拟通信器 - 统一接口
    """

    def __init__(self):
        self.mock_stm32 = MockSTM32()
        self._on_state_callback: Optional[Callable] = None

    def connect(self) -> bool:
        return self.mock_stm32.connect()

    def disconnect(self):
        self.mock_stm32.disconnect()

    def is_connected(self) -> bool:
        return self.mock_stm32.connected

    def receive_state(self) -> Optional[VehicleState]:
        """接收状态"""
        return self.mock_stm32.receive()

    def send_suggestion(self, alpha: float) -> bool:
        """发送建议"""
        return self.mock_stm32.send_suggestion(alpha)

    def send_warning(self, code: str, message: str) -> bool:
        """发送警告"""
        return self.mock_stm32.send_warning(code, message)