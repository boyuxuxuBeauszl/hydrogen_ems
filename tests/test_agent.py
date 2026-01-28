# tests/test_agent.py
"""
测试 DQN 智能体
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.dqn_agent import DQNAgent


def test_agent():
    print("=" * 55)
    print("  DQN 智能体测试")
    print("=" * 55)

    agent = DQNAgent()

    print(f"\n状态维度: {agent.state_dim}")
    print(f"动作数量: {agent.action_dim}")
    print(f"动作空间: {agent.action_space}")

    # 测试用例
    test_cases = [
        ("正常工况", [0.5, 0.3, 0.2, 0.0, 0.5, 0.5, 0.3, 0.0, 0.0, 0.0]),
        ("低SOC", [0.2, 0.3, 0.4, -0.1, 0.5, 0.5, 0.3, 0.0, 0.0, 0.0]),
        ("高SOC", [0.9, 0.2, 0.1, 0.1, 0.3, 0.5, 0.2, 0.0, 0.0, 0.0]),
        ("高负载", [0.5, 0.8, 0.5, 0.0, 0.7, 0.5, 0.5, 0.2, 0.0, 0.0]),
        ("低负载", [0.5, 0.1, 0.1, 0.0, 0.2, 0.5, 0.1, -0.1, 0.0, 0.0]),
    ]

    print("\n测试不同工况:")
    print("-" * 55)

    for name, obs in test_cases:
        result = agent.predict_with_confidence(obs)
        print(f"\n{name}:")
        print(f"  输入: SOC={obs[0]:.1f}, Load={obs[1]:.1f}, MPC={obs[2]:.1f}")
        print(f"  输出: α = {result['alpha']:+.3f}")
        print(f"  置信度: {result['confidence']:.2%}")
        print(f"  Q值: {result['q_value']:.4f}")

    # 性能测试
    print("\n" + "=" * 55)
    print("  性能测试")
    print("-" * 55)

    test_obs = test_cases[0][1]
    n_runs = 1000

    start = time.time()
    for _ in range(n_runs):
        agent.predict(test_obs)
    elapsed = time.time() - start

    print(f"运行次数: {n_runs}")
    print(f"总耗时: {elapsed * 1000:.1f} ms")
    print(f"单次耗时: {elapsed / n_runs * 1000:.3f} ms")
    print(f"最大频率: {n_runs / elapsed:.0f} Hz")

    print("\n测试完成！")


if __name__ == "__main__":
    test_agent()