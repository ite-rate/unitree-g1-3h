#!/usr/bin/env python3
# 附加章节：Go2 版本。保留原脚本，逻辑未改，只补了下面 3 行路径引导，
# 这样从 go2/ 目录直接运行时，也能 import 到仓库根目录的 unitree_sdk2py。
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
"""04 激光雷达：订阅 /utlidar/cloud，自己解析 PointCloud2。

这是整节课最"底层"的一节：
    - 一个点云就是一帧二进制 data，每个点 point_step 字节；
    - 点的 x/y/z 在 data 里的位置由 fields[].offset 决定；
    - 我们不依赖 ROS 2，也不依赖任何封装，直接 numpy 解。

用法:
    python3 04_lidar.py --seconds 10
    python3 04_lidar.py --plot                  # 另存一张俯视图
    python3 04_lidar.py --switch off            # 关雷达（官方示例里的开关）
    python3 04_lidar.py --switch on             # 再打开

课堂演示:
    先开着雷达跑 --seconds 10，看到有数据；
    再 --switch off，然后另开终端 ros2 topic hz /utlidar/cloud，会看到没有输出；
    最后 --switch on 恢复。这就是"topic 没数据"最真实的一课。
"""
import argparse
import math
import time
from pathlib import Path

import numpy as np

from unitree_sdk2py.core.channel import (
    ChannelFactoryInitialize,
    ChannelPublisher,
    ChannelSubscriber,
)
from unitree_sdk2py.idl.default import std_msgs_msg_dds__String_
from unitree_sdk2py.idl.sensor_msgs.msg.dds_ import PointCloud2_
from unitree_sdk2py.idl.std_msgs.msg.dds_ import String_

OUT = Path(__file__).resolve().parent / "out"


def parse_xyz(msg: PointCloud2_):
    """从 PointCloud2 里取出 (N, 3) 的 float32 坐标。"""
    step = msg.point_step
    total = msg.width * msg.height
    if step <= 0 or total <= 0:
        return None

    raw = np.frombuffer(bytes(msg.data), dtype=np.uint8)
    if raw.size < total * step:
        return None

    offsets = {f.name: f.offset for f in msg.fields}
    if not {"x", "y", "z"} <= offsets.keys():
        return None

    rows = raw[: total * step].reshape(total, step)
    xyz = np.empty((total, 3), dtype=np.float32)
    for i, name in enumerate(("x", "y", "z")):
        off = offsets[name]
        # 先 copy 再 view，避免非 4 字节对齐的切片报错
        xyz[:, i] = rows[:, off:off + 4].copy().view(np.float32).ravel()
    return xyz


def set_switch(on: bool, iface):
    if iface:
        ChannelFactoryInitialize(0, iface)
    else:
        ChannelFactoryInitialize(0)

    pub = ChannelPublisher("rt/utlidar/switch", String_)
    pub.Init()
    cmd = std_msgs_msg_dds__String_()
    cmd.data = "ON" if on else "OFF"
    pub.Write(cmd)
    print(f"已发送 rt/utlidar/switch = {cmd.data}")
    print("等 2~3 秒后，用 ros2 topic hz /utlidar/cloud 验证。")


def main():
    parser = argparse.ArgumentParser(description="订阅并解析 Go2 激光雷达点云")
    parser.add_argument("--iface", help="网卡名，如 eth0；不填则用 CYCLONEDDS_URI")
    parser.add_argument("--seconds", type=float, default=10.0, help="观察时长")
    parser.add_argument("--switch", choices=["on", "off"], help="只开关雷达，不订阅")
    parser.add_argument("--plot", action="store_true", help="结束后保存俯视图 PNG")
    args = parser.parse_args()

    if args.switch:
        set_switch(args.switch == "on", args.iface)
        return

    if args.iface:
        ChannelFactoryInitialize(0, args.iface)
    else:
        ChannelFactoryInitialize(0)

    box = {"frames": 0, "last": None, "pts": None, "last_t": 0.0}

    def on_cloud(msg: PointCloud2_):
        box["frames"] += 1
        now = time.monotonic()
        # 每秒最多解析 2 帧，够课堂看，也不让回调太慢
        if now - box["last_t"] < 0.5:
            return
        box["last_t"] = now

        xyz = parse_xyz(msg)
        if xyz is None:
            return
        xyz = xyz[np.isfinite(xyz).all(axis=1)]
        r = np.hypot(xyz[:, 0], xyz[:, 1])
        keep = r > 0.05  # 去掉雷达自身的零点和无效点
        xyz, r = xyz[keep], r[keep]
        if len(xyz) == 0:
            return

        i = int(np.argmin(r))
        angle = math.degrees(math.atan2(xyz[i, 1], xyz[i, 0]))

        # 正前方 2 m 宽走廊里最近的点
        front = xyz[(xyz[:, 0] > 0.1) & (np.abs(xyz[:, 1]) < 1.0)]
        front_min = float(np.hypot(front[:, 0], front[:, 1]).min()) if len(front) else float("nan")

        box["last"] = (len(xyz), float(r[i]), angle, front_min)
        # 抽稀后留给最后的俯视图
        box["pts"] = xyz[:: max(1, len(xyz) // 20000)]

    sub = ChannelSubscriber("rt/utlidar/cloud", PointCloud2_)
    sub.Init(on_cloud, 1)  # 点云帧很大，队列 1，只保留最新一帧
    print(f"订阅 rt/utlidar/cloud，观察 {args.seconds:.0f} s ...")
    print("（点云频率与固件/场景有关，以实测为准）")

    t0 = time.time()
    while time.time() - t0 < args.seconds:
        time.sleep(1.0)
        if box["last"] is None:
            print("  等待第一帧点云 ...")
            continue
        n, nearest, angle, front_min = box["last"]
        print(
            f"  已收 {box['frames']} 帧 | 本帧 {n} 点 | "
            f"最近 {nearest:.2f} m @ {angle:+.0f}° | 前方 {front_min:.2f} m"
        )

    sub.Close()

    if box["frames"] == 0:
        print("\n[失败] 没有收到 /utlidar/cloud。优先怀疑：")
        print("  1. 雷达被关了：python3 04_lidar.py --switch on")
        print("  2. 网卡/CYCLONEDDS_URI 不对（先用 00_probe.py 确认 lowstate 通）")
        print("  3. 机器人型号/固件不提供这个 topic")
        return

    if args.plot and box["pts"] is not None:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        OUT.mkdir(exist_ok=True)
        path = OUT / "lidar_topview.png"
        pts = box["pts"]
        plt.figure(figsize=(6, 6))
        plt.scatter(pts[:, 1], pts[:, 0], s=1, c=pts[:, 2], cmap="viridis")
        plt.xlim(-5, 5)
        plt.ylim(-5, 5)
        plt.xlabel("y (m)")
        plt.ylabel("x (m)  [机器人正前方 = +x]")
        plt.title("Go2 /utlidar/cloud top view")
        plt.colorbar(label="z (m)")
        plt.tight_layout()
        plt.savefig(path, dpi=130)
        print(f"\n俯视图已保存: {path}")


if __name__ == "__main__":
    main()
