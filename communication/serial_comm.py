# communication/serial_comm.py
"""
串口通信模块 - 与真实 STM32 通信
"""

import serial
import time
import threading
from typing import Optional, Callable
from queue import Queue, Empty
from communication.protocol import (
    VehicleState, Suggestion, HealthWarning,
    parse_state_message
)


class SerialCommunicator:
    """
    串口通信器
    使用独立线程接收数据，避免阻塞主循环
    """

    def __init__(self, port: str = '/dev/ttyUSB0', baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.ser: Optional[serial.Serial] = None

        # 接收缓冲
        self._rx_queue: Queue = Queue(maxsize=100)
        self._rx_thread: Optional[threading.Thread] = None
        self._running = False

        # 状态
        self.connected = False
        self.last_receive_time = 0.0

    def connect(self) -> bool:
        """建立串口连接"""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.1,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            time.sleep(2)  # 等待串口稳定

            # 启动接收线程
            self._running = True
            self._rx_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self._rx_thread.start()

            self.connected = True
            print(f"[串口] 已连接: {self.port} @ {self.baudrate}")
            return True

        except Exception as e:
            print(f"[串口] 连接失败: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """断开连接"""
        self._running = False
        if self._rx_thread:
            self._rx_thread.join(timeout=1.0)
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.connected = False
        print("[串口] 已断开")

    def is_connected(self) -> bool:
        return self.connected and self.ser and self.ser.is_open

    def _receive_loop(self):
        """接收线程"""
        buffer = ""
        while self._running:
            try:
                if self.ser and self.ser.in_waiting > 0:
                    data = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                    buffer += data

                    # 按行处理
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        if line.startswith('$STATE'):
                            state = parse_state_message(line)
                            if state:
                                # 放入队列
                                if self._rx_queue.full():
                                    try:
                                        self._rx_queue.get_nowait()
                                    except Empty:
                                        pass
                                self._rx_queue.put(state)
                                self.last_receive_time = time.time()

                time.sleep(0.001)  # 1ms

            except Exception as e:
                print(f"[串口] 接收错误: {e}")
                time.sleep(0.1)

    def receive_state(self) -> Optional[VehicleState]:
        """获取最新状态"""
        try:
            return self._rx_queue.get_nowait()
        except Empty:
            return None

    def send_suggestion(self, alpha: float) -> bool:
        """发送修正建议"""
        if not self.is_connected():
            return False

        try:
            suggestion = Suggestion(alpha=alpha)
            message = suggestion.to_message()
            self.ser.write(message.encode('utf-8'))
            return True
        except Exception as e:
            print(f"[串口] 发送失败: {e}")
            return False

    def send_warning(self, code: str, message: str) -> bool:
        """发送警告"""
        if not self.is_connected():
            return False

        try:
            warning = HealthWarning(code=code, message=message)
            msg = warning.to_message()
            self.ser.write(msg.encode('utf-8'))
            return True
        except Exception as e:
            print(f"[串口] 发送警告失败: {e}")
            return False