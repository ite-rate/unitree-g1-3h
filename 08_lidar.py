#!/usr/bin/env python3
"""08 激光雷达：G1 头部的 Livox MID-360S，看它"看到"了多远的东西。

雷达自己往外打激光测距，一帧就是周围一圈几万个 (x, y, z)。
它是独立的网络设备，要先启动驱动才有数据发成 topic：

    source ~/ws_livox/install/setup.bash
    ros2 launch livox_ros_driver2 rviz_MID360s_launch.py

★ 想直接"看"点云，就用上面这条 rviz_ 版 launch —— 它自带 RViz 窗口，
  里面就是实时点云，鼠标拖动旋转。完整步骤见 docs/lidar_setup.md。
本脚本是文字版：每秒打印一次点数和最近距离。

用法:
    python3 08_lidar.py
    python3 08_lidar.py --seconds 20
    python3 08_lidar.py --topic rt/utlidar/cloud_livox_mid360   # 机器人自带雷达服务

课堂演示：拿一块纸板靠近机器人头部，看"最近距离"跟着变小。
"""
import argparse
import time

import numpy as np

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.sensor_msgs.msg.dds_ import PointCloud2_

DEFAULT_TOPIC = "rt/livox/lidar"   # ROS 2 的 /livox/lidar 在 DDS 层叫这个名字

box = {"frames": 0, "last": None}


def on_cloud(msg: PointCloud2_):
    box["frames"] += 1
    box["last"] = msg   # 一帧点云很大，回调里只存最新一帧


def nearest_distance(msg: PointCloud2_):
    """从 PointCloud2 里取出 (N, 3) 坐标，返回 (点数, 最近距离 m)。

    data 是一整块字节：每 point_step 个字节是一个点，
    x / y / z 的位置由 fields 里的 offset 给出（float32）。
    """
    step, total = msg.point_step, msg.width * msg.height
    if step <= 0 or total <= 0:
        return None
    offsets = {f.name: f.offset for f in msg.fields}
    if not {"x", "y", "z"} <= offsets.keys():
        return None
    raw = np.frombuffer(bytes(msg.data), dtype=np.uint8)
    if raw.size < total * step:
        return None
    rows = raw[: total * step].reshape(total, step)
    xyz = np.stack([rows[:, offsets[a]:offsets[a] + 4].copy().view(np.float32).ravel()
                     for a in ("x", "y", "z")], axis=1)
    dist = np.linalg.norm(xyz, axis=1)
    dist = dist[np.isfinite(dist) & (dist > 0.1)]   # 去掉 0 点和无效点
    return dist.size, float(dist.min()) if dist.size else None


def main():
    parser = argparse.ArgumentParser(description="订阅 G1 头部激光雷达的点云")
    parser.add_argument("--seconds", type=float, default=10.0, help="观察多久")
    parser.add_argument("--topic", default=DEFAULT_TOPIC, help=f"点云 topic，默认 {DEFAULT_TOPIC}")
    args = parser.parse_args()

    ChannelFactoryInitialize(0)
    sub = ChannelSubscriber(args.topic, PointCloud2_)
    sub.Init(on_cloud, 1)   # 队列 1：只关心最新一帧
    print(f"订阅 {args.topic}，观察 {args.seconds:.0f} 秒（想看画面用 RViz，见 docs/lidar_setup.md）...")

    frames_last = 0
    t0 = time.monotonic()
    try:
        while time.monotonic() - t0 < args.seconds:
            time.sleep(1.0)
            hz, frames_last = box["frames"] - frames_last, box["frames"]
            msg = box["last"]
            if msg is None:
                print("  还没收到点云 ...")
                continue
            got = nearest_distance(msg)
            if got is None or got[1] is None:
                print(f"  {hz} 帧/秒 | 这一帧没有有效点")
            else:
                n, nearest = got
                print(f"  {hz} 帧/秒 | {n} 个点 | 最近 {nearest:.2f} m")
    finally:
        sub.Close()

    if box["frames"] == 0:
        print("\n[失败] 没收到点云，按顺序查（详见 docs/lidar_setup.md）：")
        print("  1. 雷达驱动启动了吗？（rviz_MID360s_launch.py，不要用 msg_ 版）")
        print("  2. ros2 topic hz /livox/lidar 有没有数？没有多半是 IP 配错")
        print("  3. 驱动终端和本终端都 source scripts/env.sh 了吗？")


if __name__ == "__main__":
    main()
