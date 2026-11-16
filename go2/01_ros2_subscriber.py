#!/usr/bin/env python3
# 附加章节：Go2 版本。保留原脚本，逻辑未改，只补了下面 3 行路径引导，
# 这样从 go2/ 目录直接运行时，也能 import 到仓库根目录的 unitree_sdk2py。
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
"""01 ROS 2 原生订阅者：不用 SDK，直接读 /lowstate。

ROS 2 的最小模型只有四件事：
    Node（节点） -> Topic（话题） -> Message（消息） -> Callback（回调）

这个文件就是最朴素的 rclpy 写法：没有基类、没有封装、没有配置文件。
对照 00_probe.py 看：同一个数据，SDK 里叫 rt/lowstate，ROS 2 里叫 /lowstate。

用法（先 source scripts/env.sh）:
    python3 01_ros2_subscriber.py
"""
import time

import rclpy
from rclpy.node import Node
from unitree_go.msg import LowState


class LowStateWatcher(Node):
    def __init__(self):
        super().__init__("lowstate_watcher")
        self.count = 0
        self.last = None
        self.t_last = time.monotonic()
        self.count_last = 0

        # 订阅 /lowstate，队列长度 10。第 4 个参数是 QoS 的简化写法（深度）。
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

        temps = [m.motor_state[i].temperature for i in range(12)]
        self.get_logger().info(
            f"累计 {self.count} 条 | 最近 {rate:.0f} Hz | "
            f"电量 {m.bms_state.soc}% | yaw {m.imu_state.rpy[2]:+.2f} rad | "
            f"电机温度 {min(temps)}~{max(temps)} C"
        )


def main():
    rclpy.init()
    node = LowStateWatcher()
    try:
        rclpy.spin(node)  # 阻塞在这里，消息一到就进 on_msg
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
