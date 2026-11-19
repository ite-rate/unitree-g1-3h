#!/usr/bin/env python3
"""01 ROS 2 原生订阅者：不用 SDK，直接读 G1 的 /lowstate。

ROS 2 最小模型只有四件事：Node -> Topic -> Message -> Callback。
这个文件就是最朴素的 rclpy 写法，没有基类、没有封装。

对照 00_probe.py：同一份数据，SDK 里叫 rt/lowstate，ROS 2 里叫 /lowstate，
消息类型从 unitree_hg.msg 的 LowState_ 变成 unitree_hg.msg 的 LowState。

用法（先 source scripts/env.sh）:
    python3 01_ros2_subscriber.py
"""
import time

import rclpy
from rclpy.node import Node
from unitree_hg.msg import LowState


class G1LowStateWatcher(Node):
    def __init__(self):
        super().__init__("g1_lowstate_watcher")
        self.count = 0
        self.count_last = 0
        self.t_last = time.monotonic()
        self.last = None

        # 订阅 /lowstate。第 4 个参数 10 是 QoS 的简化写法（队列深度）。
        self.create_subscription(LowState, "/lowstate", self.on_msg, 10)
        # 每秒打印一次，避免刷屏。
        self.create_timer(1.0, self.report)

    def on_msg(self, msg):
        self.count += 1
        self.last = msg

    def report(self):
        dt = time.monotonic() - self.t_last
        rate = (self.count - self.count_last) / dt
        self.t_last = time.monotonic()
        self.count_last = self.count

        m = self.last
        if m is None:
            self.get_logger().info("还没收到 /lowstate，检查网卡和 ROS_DOMAIN_ID")
            return
        self.get_logger().info(
            f"累计 {self.count} 条 | {rate:.0f} Hz | "
            f"yaw {m.imu_state.rpy[2]:+.2f} rad | "
            f"左膝 q {m.motor_state[3].q:+.3f} rad"
        )


def main():
    rclpy.init()
    node = G1LowStateWatcher()
    try:
        rclpy.spin(node)   # 阻塞在这里，消息一到就进 on_msg
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
