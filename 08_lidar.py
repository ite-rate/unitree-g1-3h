#!/usr/bin/env python3
"""08 激光雷达：G1 头部的 Livox MID-360S，看它"看到"了多远的东西。

激光雷达是什么传感器：
    自己往外打激光，测光打到物体再弹回来用了多久，换算成距离。
    MID-360S 一边打一边转，一帧就是周围一圈的几万个点，每个点是一个 (x, y, z)。
    和 00 里的 IMU、编码器不同：那些测的是机器人"自己"，雷达测的是"周围的环境"。

━━ 前置条件：先让点云出现在网络上 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
本脚本只是订阅者，不会去"打开"雷达。雷达是一台独立的网络设备，
要先有驱动把它的数据收下来、发成 topic：

    MID-360S --UDP--> livox_ros_driver2（笔记本上） --DDS--> /livox/lidar --> 本脚本

    编译一次    Livox-SDK2（master 最新版）+ livox_ros_driver2（./build.sh humble）
    改一次      config/MID360s_config.json 里的雷达 IP 和笔记本 IP
    每次上课    source scripts/env.sh
                source ~/ws_livox/install/setup.bash
                ros2 launch livox_ros_driver2 rviz_MID360s_launch.py
    验证        ros2 topic hz /livox/lidar     约 10 Hz 再跑本脚本

完整步骤和排障：docs/lidar_setup.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

本脚本只做最直观的事：每秒打印一次"这一圈有多少点、最近的东西多远、远近各占多少"。
雷达在 G1 头上是倒着装的，点的 x/y/z 要转换后才对应机器人的前后左右；
这里只用"距离"，距离和安装方向无关，不需要转换。

用法:
    python3 08_lidar.py                                        # 读驱动发的 /livox/lidar
    python3 08_lidar.py --seconds 20
    python3 08_lidar.py --topic rt/utlidar/cloud_livox_mid360  # 机器人自带雷达服务（如果有）

课堂演示：拿一块纸板在机器人头部附近慢慢靠近，看"最近距离"跟着变小。
"""
import argparse
import time

import numpy as np

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.sensor_msgs.msg.dds_ import PointCloud2_

# 驱动发的是 ROS 2 的 /livox/lidar；SDK 直接读 DDS，所以名字要写成 rt/livox/lidar。
DEFAULT_TOPIC = "rt/livox/lidar"


def parse_xyz(msg: PointCloud2_):
    """从 PointCloud2 里取出 (N, 3) 的坐标。

    点云的 data 是一整块字节：每 point_step 个字节是一个点，
    x / y / z 在一个点里的位置由 fields 里的 offset 告诉你（都是 float32）。
    """
    step = msg.point_step
    total = msg.width * msg.height
    if step <= 0 or total <= 0:
        return None

    offsets = {f.name: f.offset for f in msg.fields}
    if not {"x", "y", "z"} <= offsets.keys():
        return None

    raw = np.frombuffer(bytes(msg.data), dtype=np.uint8)
    if raw.size < total * step:
        return None

    rows = raw[: total * step].reshape(total, step)
    xyz = np.empty((total, 3), dtype=np.float32)
    for i, name in enumerate(("x", "y", "z")):
        off = offsets[name]
        xyz[:, i] = rows[:, off:off + 4].copy().view(np.float32).ravel()
    return xyz


def summarize(xyz):
    """一帧点云 -> (点数, 最近距离, 1 m 内 / 1–3 m / 3 m 外 各占多少)。"""
    xyz = xyz[np.isfinite(xyz).all(axis=1)]
    dist = np.linalg.norm(xyz, axis=1)
    dist = dist[dist > 0.1]  # 去掉 0 点和贴着雷达的无效点
    if dist.size == 0:
        return None
    near = np.mean(dist < 1.0)
    mid = np.mean((dist >= 1.0) & (dist < 3.0))
    return dist.size, float(dist.min()), near, mid, 1.0 - near - mid


def main():
    parser = argparse.ArgumentParser(description="订阅 G1 头部激光雷达的点云")
    parser.add_argument("--iface", help="网卡名，如 eth0；不填则用 CYCLONEDDS_URI")
    parser.add_argument("--seconds", type=float, default=10.0, help="观察多久")
    parser.add_argument("--topic", default=DEFAULT_TOPIC, help=f"点云 topic（DDS 名），默认 {DEFAULT_TOPIC}")
    args = parser.parse_args()

    if args.iface:
        ChannelFactoryInitialize(0, args.iface)
    else:
        ChannelFactoryInitialize(0)

    box = {"frames": 0, "last": None}

    # 点云一帧很大：回调里只保存最新一帧，解析放到主循环里，每秒做一次。
    def on_cloud(msg: PointCloud2_):
        box["frames"] += 1
        box["last"] = msg

    sub = ChannelSubscriber(args.topic, PointCloud2_)
    sub.Init(on_cloud, 1)  # 队列 1：只关心最新一帧
    print(f"订阅 {args.topic}，观察 {args.seconds:.0f} s ...")

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
            xyz = parse_xyz(msg)
            stat = summarize(xyz) if xyz is not None else None
            if stat is None:
                print(f"  {hz} 帧/秒 | 这一帧没有有效点")
                continue
            n, nearest, near, mid, far = stat
            print(f"  {hz} 帧/秒 | {n} 个点 | 最近 {nearest:.2f} m | "
                  f"1 m 内 {near:.0%}  1–3 m {mid:.0%}  3 m 外 {far:.0%}")
    except KeyboardInterrupt:
        pass
    finally:
        sub.Close()

    if box["frames"] == 0:
        print("\n[失败] 没收到点云。按这个顺序查（详见 docs/lidar_setup.md）：")
        print("  1. 雷达驱动启动了吗？ros2 launch livox_ros_driver2 rviz_MID360s_launch.py")
        print("  2. ros2 topic hz /livox/lidar 有没有数？没有就看驱动终端的报错（多半是 IP 配错）")
        print("  3. 用的是 rviz_ 版 launch 吗？msg_ 版发的是 Livox 自定义格式，本脚本读不了")
        print("  4. 驱动终端和本终端都 source 了 scripts/env.sh 吗？（RMW 和 domain 要一致）")

if __name__ == "__main__":
    main()
