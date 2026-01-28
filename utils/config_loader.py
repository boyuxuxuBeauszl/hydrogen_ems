# utils/config_loader.py
"""
配置加载器 - 读取 YAML 配置文件
"""

import os
import yaml
from typing import Any, Dict


class ConfigLoader:
    """配置文件加载器"""

    _instance = None
    _config = None

    def __new__(cls):
        """单例模式，确保全局只有一份配置"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, config_path: str = None) -> Dict:
        """
        加载配置文件

        Args:
            config_path: 配置文件路径，默认为 config/config.yaml
        """
        if config_path is None:
            # 获取项目根目录
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(root_dir, 'config', 'config.yaml')

        if not os.path.exists(config_path):
            print(f"[警告] 配置文件不存在: {config_path}，使用默认配置")
            self._config = self._default_config()
        else:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            print(f"[配置] 已加载: {config_path}")

        return self._config

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置项（支持点号分隔的路径）

        示例:
            config.get('health.soc_critical_low')  # 返回 0.15
            config.get('loop.main_freq_hz')        # 返回 10
        """
        if self._config is None:
            self.load()

        keys = key_path.split('.')
        value = self._config

        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    @property
    def config(self) -> Dict:
        """获取完整配置"""
        if self._config is None:
            self.load()
        return self._config

    def _default_config(self) -> Dict:
        """默认配置（配置文件不存在时使用）"""
        return {
            'system': {'debug_mode': True},
            'communication': {'type': 'mock'},
            'loop': {
                'main_freq_hz': 10,
                'supervisor_freq_hz': 5,
                'health_check_freq_hz': 1,
                'record_freq_hz': 10
            },
            'agent': {
                'alpha_min': -0.1,
                'alpha_max': 0.1,
                'smoothing_enabled': True,
                'smoothing_factor': 0.3
            },
            'health': {
                'soc_critical_low': 0.15,
                'soc_warning_low': 0.25,
                'comm_timeout_sec': 2.0
            },
            'recording': {
                'enabled': True,
                'output_dir': 'data',
                'format': 'csv'
            }
        }


# 全局配置实例
config = ConfigLoader()