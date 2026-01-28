# main.py
"""
氢电混动车智能监督系统 - 主程序

功能:
- 接收 STM32 状态数据
- DQN 计算 MPC 修正建议
- 健康状态监测
- 数据记录

按 Ctrl+C 安全退出
"""

import sys
import os
import time
import signal

# 添加项目根目录到路径
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

from utils.config_loader import config
from utils.logger import get_logger
from communication.mock_comm import MockCommunicator
from communication.serial_comm import SerialCommunicator
from modules.state_manager import StateManager
from modules.supervisor import DQNSupervisor
from modules.health_monitor import HealthMonitor
from modules.data_recorder import DataRecorder


class HydrogenEMSupervisor:
    """
    氢电混动车智能监督系统主类
    """

    def __init__(self):
        # 加载配置
        config.load(os.path.join(ROOT_DIR, 'config', 'config.yaml'))

        # 初始化日志
        self.logger = get_logger('main')
        self.logger.info("=" * 50)
        self.logger.info("  氢电混动车智能监督系统")
        self.logger.info("=" * 50)

        # 初始化通信
        comm_type = config.get('communication.type', 'mock')
        self.logger.info(f"通信模式: {comm_type}")

        if comm_type == 'serial':
            port = config.get('communication.serial.port', '/dev/ttyUSB0')
            baudrate = config.get('communication.serial.baudrate', 115200)
            self.comm = SerialCommunicator(port=port, baudrate=baudrate)
        else:
            self.comm = MockCommunicator()

        # 初始化各模块
        self.state_manager = StateManager()
        self.supervisor = DQNSupervisor(self.state_manager)
        self.health_monitor = HealthMonitor(self.state_manager)
        self.recorder = DataRecorder()

        # 循环控制
        self.main_freq = config.get('loop.main_freq_hz', 10)
        self.supervisor_freq = config.get('loop.supervisor_freq_hz', 5)
        self.health_freq = config.get('loop.health_check_freq_hz', 1)

        # 状态
        self._running = False
        self._cycle_count = 0
        self._last_supervisor_time = 0
        self._last_health_time = 0
        self._last_alpha = 0.0
        self._last_confidence = 0.0

        self.logger.info("初始化完成")

    def start(self):
        """启动系统"""
        self.logger.info("启动系统...")

        # 连接通信
        if not self.comm.connect():
            self.logger.error("通信连接失败！")
            return False

        self._running = True
        self._cycle_count = 0

        self.logger.info(f"主循环频率: {self.main_freq} Hz")
        self.logger.info(f"监督频率: {self.supervisor_freq} Hz")
        self.logger.info(f"健康检查频率: {self.health_freq} Hz")
        self.logger.info("-" * 50)
        self.logger.info("系统运行中... (Ctrl+C 退出)")
        self.logger.info("-" * 50)

        return True

    def stop(self):
        """停止系统"""
        self.logger.info("停止系统...")
        self._running = False
        self.comm.disconnect()
        self.recorder.close()
        self.logger.info("系统已停止")

    def run_once(self) -> bool:
        """
        执行一次主循环

        Returns:
            是否继续运行
        """
        if not self._running:
            return False

        current_time = time.time()
        self._cycle_count += 1

        # ===== 1. 接收状态 =====
        state = self.comm.receive_state()

        if state:
            # 更新状态管理器
            self.state_manager.update(state)
            self.health_monitor.update_state_time()

            # ===== 2. DQN 监督 (按配置频率) =====
            if current_time - self._last_supervisor_time >= 1.0 / self.supervisor_freq:
                result = self.supervisor.compute_suggestion()
                if result:
                    self._last_alpha = result['alpha']
                    self._last_confidence = result['confidence']

                    # 发送建议给 STM32
                    self.comm.send_suggestion(self._last_alpha)

                self._last_supervisor_time = current_time

            # ===== 3. 健康检查 (按配置频率) =====
            health_issues = []
            if current_time - self._last_health_time >= 1.0 / self.health_freq:
                issues = self.health_monitor.check()
                health_issues = [i.code for i in issues]

                # 发送警告给 STM32
                for warning in self.health_monitor.get_warnings_for_stm32():
                    self.comm.send_warning(warning.code, warning.message)

                self._last_health_time = current_time

            # ===== 4. 数据记录 =====
            self.recorder.record(
                state=state,
                cycle_count=self._cycle_count,
                dqn_alpha=self._last_alpha,
                dqn_confidence=self._last_confidence,
                health_ok=self.health_monitor.is_healthy,
                health_issues=health_issues
            )

            # ===== 5. 状态显示 (每10次循环) =====
            if self._cycle_count % 10 == 0:
                self._print_status(state)

        return True

    def _print_status(self, state):
        """打印状态信息"""
        health_str = "✓" if self.health_monitor.is_healthy else "✗"

        print(f"\r[{self._cycle_count:06d}] "
              f"SOC:{state.soc:5.1%} "
              f"V:{state.voltage_V:5.1f}V "
              f"Load:{state.load_power_W:6.1f}W "
              f"H2:{state.h2_level:5.1%} "
              f"Human:{state.human_input:+5.2f} "
              f"MPC:{state.mpc_output:5.3f} "
              f"α:{self._last_alpha:+6.3f} "
              f"[{health_str}]",
              end='', flush=True)

    def run(self):
        """主循环"""
        if not self.start():
            return

        loop_interval = 1.0 / self.main_freq

        try:
            while self._running:
                loop_start = time.time()

                # 执行一次循环
                self.run_once()

                # 控制循环频率
                elapsed = time.time() - loop_start
                if elapsed < loop_interval:
                    time.sleep(loop_interval - elapsed)

        except KeyboardInterrupt:
            print()  # 换行
            self.logger.info("收到中断信号")
        except Exception as e:
            self.logger.error(f"运行错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.stop()


# ============================================================
#  程序入口
# ============================================================

def main():
    """主函数"""
    supervisor = HydrogenEMSupervisor()

    # 注册信号处理
    def signal_handler(sig, frame):
        supervisor._running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 运行
    supervisor.run()


if __name__ == "__main__":
    main()