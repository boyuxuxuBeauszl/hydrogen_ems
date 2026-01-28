# modules/state_manager.py
"""
状态管理器 - 维护系统状态，计算趋势
"""

import time
from collections import deque
from typing import Optional, List, Dict
from communication.protocol import VehicleState


class StateManager:
    """
    状态管理器

    功能:
    - 存储历史状态
    - 计算趋势 (SOC 变化、负载变化等)
    - 为 DQN 准备输入状态
    """

    def __init__(self, history_size: int = 100):
        """
        Args:
            history_size: 保留多少历史状态
        """
        self.history_size = history_size
        self._history: deque = deque(maxlen=history_size)

        # 上一次的 DQN 动作
        self._last_alpha = 0.0
        self._alpha_history: deque = deque(maxlen=10)

        # 时间相关
        self._start_time = time.time()
        self._total_duration = 3600.0  # 假设总时长 1 小时

    def update(self, state: VehicleState):
        """更新状态"""
        self._history.append(state)

    def update_alpha(self, alpha: float):
        """更新 DQN 动作"""
        self._alpha_history.append(alpha)
        self._last_alpha = alpha

    @property
    def current_state(self) -> Optional[VehicleState]:
        """获取当前状态"""
        if len(self._history) > 0:
            return self._history[-1]
        return None

    @property
    def previous_state(self) -> Optional[VehicleState]:
        """获取上一状态"""
        if len(self._history) > 1:
            return self._history[-2]
        return None

    def get_soc_trend(self) -> float:
        """
        计算 SOC 变化趋势
        正值表示充电，负值表示放电
        """
        if len(self._history) < 2:
            return 0.0

        # 取最近几个点计算趋势
        recent = list(self._history)[-10:]
        if len(recent) < 2:
            return 0.0

        soc_values = [s.soc for s in recent]
        trend = (soc_values[-1] - soc_values[0]) / len(soc_values)

        # 归一化到 [-1, 1]
        return max(-1.0, min(1.0, trend * 100))

    def get_load_trend(self) -> float:
        """计算负载变化趋势"""
        if len(self._history) < 2:
            return 0.0

        recent = list(self._history)[-5:]
        if len(recent) < 2:
            return 0.0

        load_values = [s.load_power_W for s in recent]
        trend = (load_values[-1] - load_values[0]) / max(load_values[0], 1)

        return max(-1.0, min(1.0, trend))

    def get_alpha_trend(self) -> float:
        """计算动作变化趋势"""
        if len(self._alpha_history) < 2:
            return 0.0

        alphas = list(self._alpha_history)
        trend = alphas[-1] - alphas[0]
        return max(-1.0, min(1.0, trend * 10))

    def get_time_progress(self) -> float:
        """获取时间进度 (0-1)"""
        elapsed = time.time() - self._start_time
        return min(1.0, elapsed / self._total_duration)

    def get_dqn_state(self) -> Optional[List[float]]:
        """
        获取 DQN 输入状态 (10 维)
        """
        state = self.current_state
        if state is None:
            return None

        # 基础状态转换
        dqn_state = state.to_dqn_state()

        # 填入趋势和历史相关的值
        dqn_state[3] = self.get_soc_trend()  # SOC_trend
        dqn_state[5] = self.get_time_progress()  # time_progress
        dqn_state[7] = self.get_load_trend()  # delta_pload_norm
        dqn_state[8] = self._last_alpha * 10  # alpha_current (归一化)
        dqn_state[9] = self.get_alpha_trend()  # alpha_trend

        return dqn_state

    def get_state_summary(self) -> Dict:
        """获取状态摘要 (用于显示)"""
        state = self.current_state
        if state is None:
            return {}

        return {
            'SOC': f"{state.soc:.1%}",
            'Voltage': f"{state.voltage_V:.1f}V",
            'Current': f"{state.current_A:.1f}A",
            'Load': f"{state.load_power_W:.0f}W",
            'H2': f"{state.h2_level:.1%}",
            'Temp': f"{state.temperature_C:.1f}°C",
            'Human': f"{state.human_input:+.2f}",
            'MPC': f"{state.mpc_output:.3f}"
        }