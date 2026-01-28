# utils/logger.py
"""
日志工具 - 统一的日志输出
"""

import os
import sys
import logging
from datetime import datetime
from typing import Optional


class Logger:
    """日志管理器"""

    _loggers = {}

    @classmethod
    def get_logger(cls, name: str, log_dir: str = "logs",
                   level: str = "INFO", console: bool = True,
                   file: bool = True) -> logging.Logger:
        """
        获取日志记录器

        Args:
            name: 日志名称（通常用模块名）
            log_dir: 日志文件目录
            level: 日志级别
            console: 是否输出到控制台
            file: 是否输出到文件
        """
        if name in cls._loggers:
            return cls._loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.upper()))
        logger.handlers = []  # 清除已有处理器

        # 格式
        formatter = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )

        # 控制台输出
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        # 文件输出
        if file:
            os.makedirs(log_dir, exist_ok=True)
            date_str = datetime.now().strftime('%Y%m%d')
            log_file = os.path.join(log_dir, f"{name}_{date_str}.log")
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        cls._loggers[name] = logger
        return logger


def get_logger(name: str) -> logging.Logger:
    """快捷方式获取日志器"""
    return Logger.get_logger(name)