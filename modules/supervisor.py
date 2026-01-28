# modules/supervisor.py
"""
DQN 监督模块 - 提供 MPC 修正建议
"""

import time
from typing import Optional, Dict, List
from core.dqn_agent import DQNAgent
from modules.state_manager import StateManager
from utils.config_loader import config


class DQNSupervisor:
    """
    DQN 监督器

    功能:
    - 接收状态，计算修正建议 α
    - 平滑输出，防止剧烈跳变
    - 记录决策历史
    """

    def __init__(self, state_manager: StateManager):
        """
        Args:
            state_manager: 状态管理器实例
        """
        self.state_manager = state_manager
        self.agent = DQNAgent()

        # 配置
        self.alpha_min = config.get('agent.alpha_min', -0.1)
        self.alpha_max = config.get('agent.alpha_max', 0.1)
        self.smoothing_enabled = config.get('agent.smoothing_enabled', True)
        self.smoothing_factor = config.get('agent.smoothing_factor', 0.3)

        # 状态
        self._last_alpha = 0.0
        self._last_compute_time = 0.0
        self._compute_count = 0

        print(f"[Supervisor] 初始化完成")
        print(f"  α 范围: [{self.alpha_min}, {self.alpha_max}]")
        print(f"  平滑: {self.smoothing_enabled}, 因子: {self.smoothing_factor}")

    def compute_suggestion(self) -> Optional[Dict]:
        """
        计算修正建议

        Returns:
            {
                'alpha': float,         # 修正值
                'alpha_raw': float,     # 原始值 (平滑前)
                'confidence': float,    # 置信度
                'state_input': list     # DQN 输入状态
            }
        """
        # 获取 DQN 输入状态
        dqn_state = self.state_manager.get_dqn_state()
        if dqn_state is None:
            return None

        # DQN 推理
        result = self.agent.predict_with_confidence(dqn_state)
        alpha_raw = result['alpha']

        # 限幅
        alpha_raw = max(self.alpha_min, min(self.alpha_max, alpha_raw))

        # 平滑
        if self.smoothing_enabled:
            alpha = self._last_alpha * (1 - self.smoothing_factor) + alpha_raw * self.smoothing_factor
        else:
            alpha = alpha_raw

        # 更新状态
        self._last_alpha = alpha
        self._last_compute_time = time.time()
        self._compute_count += 1

        # 通知状态管理器
        self.state_manager.update_alpha(alpha)

        return {
            'alpha': alpha,
            'alpha_raw': alpha_raw,
            'confidence': result['confidence'],
            'q_value': result['q_value'],
            'state_input': dqn_state
        }

    @property
    def last_alpha(self) -> float:
        return self._last_alpha

    @property
    def stats(self) -> Dict:
        """统计信息"""
        return {
            'compute_count': self._compute_count,
            'last_alpha': self._last_alpha,
            'last_compute_time': self._last_compute_time
        }
