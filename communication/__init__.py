# communication/__init__.py
"""
通信模块初始化
"""

from communication.protocol import (
    VehicleState,
    Suggestion,
    HealthWarning,
    MessageType,
    parse_state_message,
    create_state_message
)
from communication.mock_comm import MockCommunicator, MockSTM32
from communication.serial_comm import SerialCommunicator

__all__ = [
    'VehicleState',
    'Suggestion',
    'HealthWarning',
    'MessageType',
    'parse_state_message',
    'create_state_message',
    'MockCommunicator',
    'MockSTM32',
    'SerialCommunicator'
]