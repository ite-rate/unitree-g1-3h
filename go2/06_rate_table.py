#!/usr/bin/env python3
# 附加章节：Go2 版本。保留原脚本，逻辑未改，只补了下面 3 行路径引导，
# 这样从 go2/ 目录直接运行时，也能 import 到仓库根目录的 unitree_sdk2py。
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
"""06 频率与抖动：四个 topic 同时看，谁快、谁稳、谁在丢。

上一节只看"有没有数据"，这一节看"数据来得有多规律"。
同一个 DDS 网络，ros2 topic hz 和这里的计数应该接近；
如果不一致，通常是启动顺序、QoS 或回调里干了太多事。

用法:
    python3 06_rate_table.py --seconds 10
"""
import argparse
import time

import numpy as np

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.sensor_msgs.msg.dds_ import PointCloud2_
from unitree_sdk2py.idl.unitree_go.msg.dds_ import (
    LowState_,
    SportModeState_,
    WirelessController_,
)

# topic 名, 消息类型, 队列, 说明
TOPICS = [
    ("rt/lowstate", LowState_, 10, "电机/IMU/电池，高频"),
    ("rt/sportmodestate", SportModeState_, 10, "运控状态，中频"),
    ("rt/utlidar/cloud", PointCloud2_, 1, "点云，大包，低频"),
    ("rt/wirelesscontroller", WirelessController_, 10, "遥控器（不开遥控器就没有）"),
]


def main():
    parser = argparse.ArgumentParser(description="同时统计多个 Unitree topic 的频率")
    parser.add_argument("--iface", help="网卡名，如 eth0；不填则用 CYCLONEDDS_URI")
    parser.add_argument("--seconds", type=float, default=10.0, help="统计时长")
    args = parser.parse_args()

    if args.iface:
        ChannelFactoryInitialize(0, args.iface)
    else:
        ChannelFactoryInitialize(0)

    stats = {
        name: {"count": 0, "last": None, "dt": []}
        for name, _, _, _ in TOPICS
    }

    def make_handler(name):
        def handler(_msg):
            now = time.monotonic()
            s = stats[name]
            if s["last"] is not None:
                s["dt"].append(now - s["last"])
            s["last"] = now
            s["count"] += 1
        return handler

    subs = []
    for name, msg_type, queue, _ in TOPICS:
        sub = ChannelSubscriber(name, msg_type)
        sub.Init(make_handler(name), queue)
        subs.append(sub)

    print(f"统计 {args.seconds:.0f} s ...")
    time.sleep(args.seconds)
    for sub in subs:
        sub.Close()

    print(f"\n{'topic':<26}{'条数':>7}{'Hz':>9}{'间隔p50':>10}{'p95':>8}{'抖动':>8}")
    print("-" * 68)
    for name, _, _, desc in TOPICS:
        s = stats[name]
        n = s["count"]
        if n < 2:
            print(f"{name:<26}{n:>7}{'-':>9}{'-':>10}{'-':>8}{'-':>8}  {desc}")
            continue
        dt = np.array(s["dt"]) * 1000.0  # ms
        hz = 1000.0 / dt.mean()
        p50 = np.percentile(dt, 50)
        p95 = np.percentile(dt, 95)
        jitter = dt.std()
        print(f"{name:<26}{n:>7}{hz:>9.1f}{p50:>10.2f}{p95:>8.2f}{jitter:>8.2f}  {desc}")

    print("\n对照实验（另开终端，先 source scripts/env.sh）：")
    print("  ros2 topic hz /lowstate")
    print("  ros2 topic bw /utlidar/cloud")
    print("  ros2 topic info /utlidar/cloud -v")
    print("\np95 远大于 p50，说明偶发卡顿；抖动大不一定是网络，也可能是回调里做的事太重。")


if __name__ == "__main__":
    main()
