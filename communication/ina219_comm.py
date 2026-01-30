# communication/ina219_comm.py
import time
import board
import busio
from adafruit_ina219 import INA219
from communication.protocol import VehicleState
import random


class INA219Communicator:
    """
    使用 INA219 传感器作为数据源进行硬件在环测试
    """

    def __init__(self):
        try:
            i2c_bus = busio.I2C(board.SCL, board.SDA)
            self.ina219 = INA219(i2c_bus)
            self.connected = True
            print("[INA219] 传感器已连接")
        except Exception as e:
            print(f"[INA219] 连接失败: {e}")
            self.connected = False

        # 模拟的其他状态（因为传感器只能测电压电流）
        self.sim_soc = 0.6
        self.sim_h2 = 0.8

    def connect(self):
        return self.connected

    def disconnect(self):
        pass

    def receive_state(self):
        if not self.connected:
            return None

        # 1. 读取真实硬件数据
        bus_voltage = self.ina219.bus_voltage  # V
        current = self.ina219.current / 1000.0  # mA 转 A
        power = self.ina219.power  # W

        # 2. 模拟剩余数据 (因为你没有整车)
        # 简单模拟：电压越低，认为SOC越低
        self.sim_soc -= current * 0.0001  # 模拟耗电

        # 构造状态对象
        state = VehicleState(
            timestamp_ms=int(time.time() * 1000),
            soc=self.sim_soc,
            voltage_V=bus_voltage,  # <--- 真实数据！
            current_A=current,  # <--- 真实数据！
            temperature_C=25.0 + current * 2,  # 假装电流大温度高
            h2_level=self.sim_h2,
            load_power_W=power,  # <--- 真实数据！
            fc_power_W=0.0,
            mpc_output=0.5,
            human_input=0.0
        )
        return state

    def send_suggestion(self, alpha):
        print(f"[INA219测试] 收到 DQN 建议: α={alpha:.3f}")
        # 这里你可以做一个有趣的实验：
        # 如果 α > 0，你可以尝试手动拔插电阻线，看电压变化
        return True

    def send_warning(self, code, msg):
        print(f"[警告] {code}: {msg}")