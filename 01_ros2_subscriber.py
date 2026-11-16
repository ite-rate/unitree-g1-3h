#!/usr/bin/env python3
"""01 ROS 2 原生订阅者：不用 SDK，直接读 G1 的 /lowstate。

ROS 2 的最小模型只有四件事：
    Node（节点） -> Topic（话题） -> Message（消息） -> Callback（回调）

这个文件就是最朴素的 rclpy 写法：没有基类、没有封装、没有配置文件。
对照 00_probe.py 看：同一个数据，SDK 里叫 rt/lowstate，ROS 2 里叫 /lowstate。

消息类型也从 unitree_go 换成了 unitree_hg：
    from unitree_hg.msg import LowState

想先补概念，打开 docs/ros2_minimal.html，里面有 Node/Topic/DDS 的图。

用法（先 source scripts/env.sh）:
    python3 01_ros2_subscriber.py
"""
import time

import rclpy
from rclpy.node import Node
from unitree_hg.msg import LowState

# G1 29 DOF 机型：0–28 是有效关节，29–34 是预留槽位。
G1_MOTOR_COUNT = 29


class G1LowStateWatcher(Node):
    def __init__(self):
        super().__init__("g1_lowstate_watcher")
        self.count = 0
        self.last = None
        self.t_last = time.monotonic()
        self.count_last = 0

        # 订阅 /lowstate，队列长度 10。第 4 个参数是 QoS 的简化写法（深度）。
        # 对比 00_probe.py：那里是 ChannelSubscriber("rt/lowstate", LowState_)，
        # 这里 ROS 2 自动把话题名映射成 DDS 的 rt/lowstate。
        self.create_subscription(LowState, "/lowstate", self.on_msg, 10)

        # 每秒打印一次，避免刷屏。
        self.create_timer(1.0, self.report)

    def on_msg(self, msg):
        self.count += 1
        self.last = msg

    def report(self):
        now = time.monotonic()
        dt = now - self.t_last
        rate = (self.count - self.count_last) / dt if dt > 0 else 0.0
        self.t_last = now
        self.count_last = self.count

        m = self.last
        if m is None:
            self.get_logger().info("还没收到 /lowstate，检查网卡和 ROS_DOMAIN_ID")
            return

        temps = [m.motor_state[i].temperature[0] for i in range(G1_MOTOR_COUNT)]
        temps = [t for t in temps if t > 0]
        temp_text = f"{min(temps)}~{max(temps)} C" if temps else "全 0（待机？）"

        self.get_logger().info(
            f"累计 {self.count} 条 | 最近 {rate:.0f} Hz | "
            f"mode_machine {m.mode_machine} | yaw {m.imu_state.rpy[2]:+.2f} rad | "
            f"电机温度 {temp_text}"
        )


def main():
    rclpy.init()
    node = G1LowStateWatcher()
    try:
        rclpy.spin(node)  # 阻塞在这里，消息一到就进 on_msg
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
