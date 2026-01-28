# communication/protocol.py
"""
通信协议定义 - 树莓派 ↔ STM32 数据格式
============================================

【协议说明】

1. STM32 → 树莓派 (状态数据包)
   格式: $STATE,<timestamp>,<soc>,<voltage>,<current>,<temp>,<h2_level>,
          <load_power>,<mpc_output>,<human_input>,<motor1>,<motor2>,<motor3>,<motor4>*<checksum>\n

   示例: $STATE,12345,0.65,24.5,12.3,35.2,0.80,150.5,0.35,0.50,1200,1150,1180,1190*5A\n

2. 树莓派 → STM32 (修正建议)
   格式: $SUGGEST,<alpha>*<checksum>\n

   示例: $SUGGEST,0.025*3F\n

3. 树莓派 → STM32 (健康警告)
   格式: $WARN,<code>,<message>*<checksum>\n

   示例: $WARN,LOW_SOC,Battery low*2B\n

【校验和计算】
   XOR 所有 $ 和 * 之间的字符
"""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum
import time


class MessageType(Enum):
    """消息类型"""
    STATE = "STATE"  # 状态数据
    SUGGEST = "SUGGEST"  # 修正建议
    WARN = "WARN"  # 警告
    ACK = "ACK"  # 确认
    ERROR = "ERROR"  # 错误


@dataclass
class VehicleState:
    """
    车辆状态数据结构
    所有物理量都有明确的单位和含义
    """
    # 时间戳
    timestamp_ms: int = 0  # STM32 系统时间 (ms)
    receive_time: float = 0.0  # 树莓派接收时间 (Unix timestamp)

    # 电池状态
    soc: float = 0.0  # 锂电池 SOC (0-1)
    voltage_V: float = 0.0  # 电池电压 (V)
    current_A: float = 0.0  # 电池电流 (A)，正为放电
    temperature_C: float = 0.0  # 电池温度 (°C)

    # 燃料电池状态
    h2_level: float = 0.0  # 氢气剩余量 (0-1)
    fc_power_W: float = 0.0  # 燃料电池输出功率 (W)

    # 功率与控制
    load_power_W: float = 0.0  # 负载需求功率 (W)
    mpc_output: float = 0.0  # MPC 计算的功率分配 (0-1)
    human_input: float = 0.0  # 人的控制输入 (遥控器，-1 到 1)

    # 电机状态 (4个麦轮)
    motor_rpm: List[int] = None  # 各电机转速 [FL, FR, RL, RR]

    # 额外状态 (用于 DQN)
    soc_trend: float = 0.0  # SOC 变化趋势
    load_trend: float = 0.0  # 负载变化趋势

    def __post_init__(self):
        if self.motor_rpm is None:
            self.motor_rpm = [0, 0, 0, 0]
        self.receive_time = time.time()

    def to_dqn_state(self) -> List[float]:
        """
        转换为 DQN 输入格式 (10维归一化向量)

        对应:
        [0] SOC_norm         - 锂电池SOC
        [1] Load_norm        - 负载功率 (归一化到 0-1)
        [2] MPC_norm         - MPC代价函数
        [3] SOC_trend        - SOC变化趋势
        [4] Power_ratio      - 燃料电池功率比
        [5] time_progress    - 时间进度 (需要外部传入)
        [6] H2_flow_norm     - 氢气消耗
        [7] delta_pload_norm - 负载变化率
        [8] alpha_current    - 上一步动作
        [9] alpha_trend      - 动作变化趋势
        """
        # 归一化参数 (根据实际系统调整)
        MAX_LOAD_POWER = 500.0  # 最大负载功率 (W)

        return [
            self.soc,  # [0] SOC
            min(self.load_power_W / MAX_LOAD_POWER, 1),  # [1] 负载功率归一化
            self.mpc_output,  # [2] MPC 输出
            self.soc_trend,  # [3] SOC 趋势
            self.fc_power_W / MAX_LOAD_POWER if MAX_LOAD_POWER > 0 else 0,  # [4] 功率比
            0.5,  # [5] 时间进度 (占位)
            1.0 - self.h2_level,  # [6] 氢气消耗
            self.load_trend,  # [7] 负载变化率
            0.0,  # [8] 上一步动作 (由外部填入)
            0.0  # [9] 动作趋势 (由外部填入)
        ]

    def __str__(self) -> str:
        return (f"State(SOC={self.soc:.2f}, V={self.voltage_V:.1f}V, "
                f"I={self.current_A:.1f}A, Load={self.load_power_W:.0f}W)")


@dataclass
class Suggestion:
    """
    DQN 修正建议
    """
    alpha: float = 0.0  # 修正量 (-0.1 到 0.1)
    confidence: float = 0.0  # 置信度 (0-1)
    timestamp: float = 0.0  # 生成时间

    def __post_init__(self):
        self.timestamp = time.time()

    def to_message(self) -> str:
        """转换为发送消息"""
        content = f"SUGGEST,{self.alpha:.4f}"
        checksum = calculate_checksum(content)
        return f"${content}*{checksum}\n"


@dataclass
class HealthWarning:
    """
    健康警告
    """
    code: str  # 警告代码
    message: str  # 警告信息
    severity: int = 1  # 严重程度 (1=提示, 2=警告, 3=严重)
    timestamp: float = 0.0

    def __post_init__(self):
        self.timestamp = time.time()

    def to_message(self) -> str:
        """转换为发送消息"""
        content = f"WARN,{self.code},{self.message}"
        checksum = calculate_checksum(content)
        return f"${content}*{checksum}\n"


# ============================================================
#  协议解析函数
# ============================================================

def calculate_checksum(data: str) -> str:
    """计算校验和 (XOR)"""
    checksum = 0
    for char in data:
        checksum ^= ord(char)
    return f"{checksum:02X}"


def verify_checksum(message: str) -> bool:
    """验证校验和"""
    try:
        if not message.startswith('$') or '*' not in message:
            return False

        content = message[1:message.index('*')]
        received_cs = message[message.index('*') + 1:].strip()
        calculated_cs = calculate_checksum(content)

        return received_cs.upper() == calculated_cs.upper()
    except:
        return False


def parse_state_message(message: str) -> Optional[VehicleState]:
    """
    解析状态消息

    格式: $STATE,<timestamp>,<soc>,<voltage>,<current>,<temp>,<h2_level>,
           <load_power>,<mpc_output>,<human_input>,<m1>,<m2>,<m3>,<m4>*<cs>\n
    """
    try:
        # 去除首尾
        message = message.strip()

        # 验证校验和 (可选)
        # if not verify_checksum(message):
        #     return None

        # 提取内容
        if '*' in message:
            content = message[1:message.index('*')]
        else:
            content = message[1:] if message.startswith('$') else message

        parts = content.split(',')

        if parts[0] != 'STATE' or len(parts) < 13:
            return None

        state = VehicleState(
            timestamp_ms=int(parts[1]),
            soc=float(parts[2]),
            voltage_V=float(parts[3]),
            current_A=float(parts[4]),
            temperature_C=float(parts[5]),
            h2_level=float(parts[6]),
            load_power_W=float(parts[7]),
            mpc_output=float(parts[8]),
            human_input=float(parts[9]),
            motor_rpm=[int(parts[10]), int(parts[11]), int(parts[12]), int(parts[13])]
        )

        return state

    except Exception as e:
        print(f"[协议] 解析失败: {e}, 原始消息: {message}")
        return None


def create_state_message(state: VehicleState) -> str:
    """创建状态消息 (用于模拟测试)"""
    content = (f"STATE,{state.timestamp_ms},{state.soc:.3f},{state.voltage_V:.1f},"
               f"{state.current_A:.1f},{state.temperature_C:.1f},{state.h2_level:.2f},"
               f"{state.load_power_W:.1f},{state.mpc_output:.3f},{state.human_input:.2f},"
               f"{state.motor_rpm[0]},{state.motor_rpm[1]},{state.motor_rpm[2]},{state.motor_rpm[3]}")
    checksum = calculate_checksum(content)
    return f"${content}*{checksum}\n"