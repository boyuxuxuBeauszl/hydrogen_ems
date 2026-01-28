# modules/health_monitor.py
"""
健康监测模块 - 系统状态监控与异常检测
"""

import time
from typing import List, Optional, Dict
from dataclasses import dataclass
from enum import Enum
from communication.protocol import VehicleState, HealthWarning
from modules.state_manager import StateManager
from utils.config_loader import config


class HealthLevel(Enum):
    """健康等级"""
    OK = 0  # 正常
    INFO = 1  # 提示
    WARNING = 2  # 警告
    CRITICAL = 3  # 严重


@dataclass
class HealthIssue:
    """健康问题"""
    code: str  # 问题代码
    message: str  # 描述
    level: HealthLevel  # 严重程度
    value: float = 0.0  # 相关数值
    threshold: float = 0.0  # 阈值
    timestamp: float = 0.0  # 检测时间

    def __post_init__(self):
        self.timestamp = time.time()


class HealthMonitor:
    """
    健康监测器

    监测项目:
    - SOC 状态 (过高/过低)
    - 电压异常
    - 电流过大
    - 温度过高
    - 氢气不足
    - 通信超时
    """

    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager

        # 加载阈值配置
        self.thresholds = {
            'soc_critical_low': config.get('health.soc_critical_low', 0.15),
            'soc_warning_low': config.get('health.soc_warning_low', 0.25),
            'soc_warning_high': config.get('health.soc_warning_high', 0.90),
            'soc_critical_high': config.get('health.soc_critical_high', 0.95),
            'voltage_min': config.get('health.voltage_min', 20.0),
            'voltage_max': config.get('health.voltage_max', 28.0),
            'current_max': config.get('health.current_max', 50.0),
            'temp_warning': config.get('health.temp_warning', 45.0),
            'temp_critical': config.get('health.temp_critical', 60.0),
            'h2_warning': config.get('health.h2_warning', 0.20),
            'h2_critical': config.get('health.h2_critical', 0.10),
            'comm_timeout': config.get('health.comm_timeout_sec', 2.0)
        }

        # 状态
        self._issues: List[HealthIssue] = []
        self._last_state_time = time.time()
        self._last_check_time = 0.0

        print("[HealthMonitor] 初始化完成")

    def update_state_time(self):
        """更新最后收到状态的时间"""
        self._last_state_time = time.time()

    def check(self) -> List[HealthIssue]:
        """
        执行健康检查

        Returns:
            发现的问题列表
        """
        self._issues = []
        self._last_check_time = time.time()

        state = self.state_manager.current_state

        # 检查通信状态
        self._check_communication()

        if state is None:
            return self._issues

        # 检查各项指标
        self._check_soc(state)
        self._check_voltage(state)
        self._check_current(state)
        self._check_temperature(state)
        self._check_hydrogen(state)

        return self._issues

    def _check_communication(self):
        """检查通信状态"""
        elapsed = time.time() - self._last_state_time
        timeout = self.thresholds['comm_timeout']

        if elapsed > timeout:
            self._issues.append(HealthIssue(
                code='COMM_TIMEOUT',
                message=f'通信超时 ({elapsed:.1f}s > {timeout}s)',
                level=HealthLevel.CRITICAL,
                value=elapsed,
                threshold=timeout
            ))

    def _check_soc(self, state: VehicleState):
        """检查 SOC"""
        soc = state.soc

        if soc <= self.thresholds['soc_critical_low']:
            self._issues.append(HealthIssue(
                code='SOC_CRITICAL_LOW',
                message=f'电量严重不足 ({soc:.1%})',
                level=HealthLevel.CRITICAL,
                value=soc,
                threshold=self.thresholds['soc_critical_low']
            ))
        elif soc <= self.thresholds['soc_warning_low']:
            self._issues.append(HealthIssue(
                code='SOC_WARNING_LOW',
                message=f'电量偏低 ({soc:.1%})',
                level=HealthLevel.WARNING,
                value=soc,
                threshold=self.thresholds['soc_warning_low']
            ))
        elif soc >= self.thresholds['soc_critical_high']:
            self._issues.append(HealthIssue(
                code='SOC_CRITICAL_HIGH',
                message=f'电量过高 ({soc:.1%})',
                level=HealthLevel.CRITICAL,
                value=soc,
                threshold=self.thresholds['soc_critical_high']
            ))
        elif soc >= self.thresholds['soc_warning_high']:
            self._issues.append(HealthIssue(
                code='SOC_WARNING_HIGH',
                message=f'电量偏高 ({soc:.1%})',
                level=HealthLevel.WARNING,
                value=soc,
                threshold=self.thresholds['soc_warning_high']
            ))

    def _check_voltage(self, state: VehicleState):
        """检查电压"""
        voltage = state.voltage_V

        if voltage < self.thresholds['voltage_min']:
            self._issues.append(HealthIssue(
                code='VOLTAGE_LOW',
                message=f'电压过低 ({voltage:.1f}V)',
                level=HealthLevel.WARNING,
                value=voltage,
                threshold=self.thresholds['voltage_min']
            ))
        elif voltage > self.thresholds['voltage_max']:
            self._issues.append(HealthIssue(
                code='VOLTAGE_HIGH',
                message=f'电压过高 ({voltage:.1f}V)',
                level=HealthLevel.WARNING,
                value=voltage,
                threshold=self.thresholds['voltage_max']
            ))

    def _check_current(self, state: VehicleState):
        """检查电流"""
        current = abs(state.current_A)

        if current > self.thresholds['current_max']:
            self._issues.append(HealthIssue(
                code='CURRENT_HIGH',
                message=f'电流过大 ({current:.1f}A)',
                level=HealthLevel.WARNING,
                value=current,
                threshold=self.thresholds['current_max']
            ))

    def _check_temperature(self, state: VehicleState):
        """检查温度"""
        temp = state.temperature_C

        if temp >= self.thresholds['temp_critical']:
            self._issues.append(HealthIssue(
                code='TEMP_CRITICAL',
                message=f'温度过高 ({temp:.1f}°C)',
                level=HealthLevel.CRITICAL,
                value=temp,
                threshold=self.thresholds['temp_critical']
            ))
        elif temp >= self.thresholds['temp_warning']:
            self._issues.append(HealthIssue(
                code='TEMP_WARNING',
                message=f'温度偏高 ({temp:.1f}°C)',
                level=HealthLevel.WARNING,
                value=temp,
                threshold=self.thresholds['temp_warning']
            ))

    def _check_hydrogen(self, state: VehicleState):
        """检查氢气剩余量"""
        h2 = state.h2_level

        if h2 <= self.thresholds['h2_critical']:
            self._issues.append(HealthIssue(
                code='H2_CRITICAL',
                message=f'氢气严重不足 ({h2:.1%})',
                level=HealthLevel.CRITICAL,
                value=h2,
                threshold=self.thresholds['h2_critical']
            ))
        elif h2 <= self.thresholds['h2_warning']:
            self._issues.append(HealthIssue(
                code='H2_WARNING',
                message=f'氢气偏低 ({h2:.1%})',
                level=HealthLevel.WARNING,
                value=h2,
                threshold=self.thresholds['h2_warning']
            ))

    @property
    def current_issues(self) -> List[HealthIssue]:
        """获取当前问题列表"""
        return self._issues

    @property
    def has_critical(self) -> bool:
        """是否有严重问题"""
        return any(i.level == HealthLevel.CRITICAL for i in self._issues)

    @property
    def has_warning(self) -> bool:
        """是否有警告"""
        return any(i.level == HealthLevel.WARNING for i in self._issues)

    @property
    def is_healthy(self) -> bool:
        """系统是否健康"""
        return len(self._issues) == 0

    def get_warnings_for_stm32(self) -> List[HealthWarning]:
        """获取需要发送给 STM32 的警告"""
        warnings = []
        for issue in self._issues:
            if issue.level in [HealthLevel.WARNING, HealthLevel.CRITICAL]:
                warnings.append(HealthWarning(
                    code=issue.code,
                    message=issue.message,
                    severity=issue.level.value
                ))
        return warnings

    def get_status_summary(self) -> Dict:
        """获取状态摘要"""
        return {
            'is_healthy': self.is_healthy,
            'has_warning': self.has_warning,
            'has_critical': self.has_critical,
            'issue_count': len(self._issues),
            'issues': [
                {'code': i.code, 'message': i.message, 'level': i.level.name}
                for i in self._issues
            ]
        }