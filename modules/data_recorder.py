# modules/data_recorder.py
"""
数据记录模块 - 记录轨迹数据用于分析和训练
"""

import os
import csv
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from communication.protocol import VehicleState
from utils.config_loader import config


@dataclass
class TrajectoryRecord:
    """
    单条轨迹记录
    包含：时间、状态、人的输入、DQN建议、实际动作
    """
    # 时间戳
    timestamp: float  # Unix 时间戳
    time_str: str  # 可读时间字符串
    cycle_count: int  # 循环计数

    # 车辆状态
    soc: float  # 电池 SOC
    voltage_V: float  # 电压
    current_A: float  # 电流
    temperature_C: float  # 温度
    h2_level: float  # 氢气剩余量
    load_power_W: float  # 负载功率
    fc_power_W: float  # 燃料电池功率

    # 控制相关
    human_input: float  # 人的控制输入 (遥控器)
    mpc_output: float  # MPC 计算输出
    dqn_alpha: float  # DQN 建议修正量
    dqn_confidence: float  # DQN 置信度
    actual_action: float  # 实际执行的动作 (mpc + alpha)

    # 电机状态
    motor_rpm_fl: int  # 前左电机转速
    motor_rpm_fr: int  # 前右电机转速
    motor_rpm_rl: int  # 后左电机转速
    motor_rpm_rr: int  # 后右电机转速

    # 健康状态
    health_ok: bool  # 系统是否健康
    health_issues: str  # 健康问题 (逗号分隔)


class DataRecorder:
    """
    数据记录器

    功能:
    - 记录每个时间步的完整数据
    - 支持 CSV 和 JSON 格式
    - 自动分割文件
    - 可配置记录内容
    """

    # CSV 表头
    CSV_HEADERS = [
        'timestamp', 'time_str', 'cycle_count',
        'soc', 'voltage_V', 'current_A', 'temperature_C',
        'h2_level', 'load_power_W', 'fc_power_W',
        'human_input', 'mpc_output', 'dqn_alpha', 'dqn_confidence', 'actual_action',
        'motor_rpm_fl', 'motor_rpm_fr', 'motor_rpm_rl', 'motor_rpm_rr',
        'health_ok', 'health_issues'
    ]

    def __init__(self):
        # 配置
        self.enabled = config.get('recording.enabled', True)
        self.output_dir = config.get('recording.output_dir', 'data')
        self.format = config.get('recording.format', 'csv')
        self.max_rows = config.get('recording.max_rows_per_file', 10000)

        # 状态
        self._file = None
        self._writer = None
        self._current_file_path = None
        self._row_count = 0
        self._total_records = 0
        self._file_count = 0

        # 创建输出目录
        if self.enabled:
            os.makedirs(self.output_dir, exist_ok=True)
            self._open_new_file()

        print(f"[DataRecorder] 初始化完成")
        print(f"  启用: {self.enabled}")
        print(f"  目录: {self.output_dir}")
        print(f"  格式: {self.format}")

    def _open_new_file(self):
        """打开新的数据文件"""
        if self._file:
            self._file.close()

        self._file_count += 1
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if self.format == 'csv':
            filename = f"trajectory_{timestamp}_{self._file_count:03d}.csv"
            self._current_file_path = os.path.join(self.output_dir, filename)
            self._file = open(self._current_file_path, 'w', newline='', encoding='utf-8')
            self._writer = csv.DictWriter(self._file, fieldnames=self.CSV_HEADERS)
            self._writer.writeheader()
        else:  # json
            filename = f"trajectory_{timestamp}_{self._file_count:03d}.jsonl"
            self._current_file_path = os.path.join(self.output_dir, filename)
            self._file = open(self._current_file_path, 'w', encoding='utf-8')

        self._row_count = 0
        print(f"[DataRecorder] 新文件: {filename}")

    def record(self,
               state: VehicleState,
               cycle_count: int,
               dqn_alpha: float = 0.0,
               dqn_confidence: float = 0.0,
               health_ok: bool = True,
               health_issues: List[str] = None):
        """
        记录一条数据

        Args:
            state: 车辆状态
            cycle_count: 循环计数
            dqn_alpha: DQN 建议修正量
            dqn_confidence: DQN 置信度
            health_ok: 系统是否健康
            health_issues: 健康问题列表
        """
        if not self.enabled:
            return

        # 创建记录
        record = TrajectoryRecord(
            timestamp=time.time(),
            time_str=datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
            cycle_count=cycle_count,

            soc=state.soc,
            voltage_V=state.voltage_V,
            current_A=state.current_A,
            temperature_C=state.temperature_C,
            h2_level=state.h2_level,
            load_power_W=state.load_power_W,
            fc_power_W=state.fc_power_W,

            human_input=state.human_input,
            mpc_output=state.mpc_output,
            dqn_alpha=dqn_alpha,
            dqn_confidence=dqn_confidence,
            actual_action=state.mpc_output + dqn_alpha,

            motor_rpm_fl=state.motor_rpm[0],
            motor_rpm_fr=state.motor_rpm[1],
            motor_rpm_rl=state.motor_rpm[2],
            motor_rpm_rr=state.motor_rpm[3],

            health_ok=health_ok,
            health_issues=','.join(health_issues) if health_issues else ''
        )

        # 写入文件
        if self.format == 'csv':
            self._writer.writerow(asdict(record))
        else:
            self._file.write(json.dumps(asdict(record), ensure_ascii=False) + '\n')

        self._row_count += 1
        self._total_records += 1

        # 检查是否需要新文件
        if self._row_count >= self.max_rows:
            self._open_new_file()

    def flush(self):
        """刷新缓冲区"""
        if self._file:
            self._file.flush()

    def close(self):
        """关闭文件"""
        if self._file:
            self._file.close()
            self._file = None
        print(f"[DataRecorder] 已关闭，共记录 {self._total_records} 条数据")

    @property
    def stats(self) -> Dict:
        """统计信息"""
        return {
            'enabled': self.enabled,
            'total_records': self._total_records,
            'current_file': self._current_file_path,
            'current_file_rows': self._row_count,
            'file_count': self._file_count
        }