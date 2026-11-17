#!/usr/bin/env python3
"""06 频率与抖动：传感器数据多久来一次、来得稳不稳。

00、05 看的是传感器"测到了什么"；这一节看"多久测一次"。
控制机器人要用新鲜的数据：数据来得慢，或者忽快忽慢，控制就会跟着出问题。

G1 把同一批传感器读数，按两种频率广播出来：
    rt/lowstate       高频（约 500 Hz），低层控制用
    rt/lf/lowstate    低频（约 50 Hz），看状态 / 记日志用

两者消息类型相同（unitree_hg.msg.LowState），只是发布频率不同。
这一节看三件事：
    Hz          平均频率
    p50 / p95   间隔的中位数和 95 分位；p95 远大于 p50 说明偶发卡顿
    抖动        间隔的标准差

用法:
    python3 06_rate_table.py --seconds 10
    python3 06_rate_table.py --seconds 30 --iface eth0
"""
import argparse
import time

import numpy as np

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_

# topic 名, 消息类型, 队列, 说明
TOPICS = [
    ("rt/lowstate", LowState_, 10, "高频整机状态，低层控制用"),
    ("rt/lf/lowstate", LowState_, 10, "低频整机状态，看状态/记日志用"),
]


def main():
    parser = argparse.ArgumentParser(description="对比 G1 两路 /lowstate 的频率与抖动")
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

    print(f"\n{'topic':<20}{'条数':>8}{'Hz':>9}{'间隔p50':>10}{'p95':>8}{'抖动':>8}")
    print("-" * 63)
    for name, _, _, desc in TOPICS:
        s = stats[name]
        n = s["count"]
        if n < 2:
            print(f"{name:<20}{n:>8}{'-':>9}{'-':>10}{'-':>8}{'-':>8}  {desc}")
            continue
        dt = np.array(s["dt"]) * 1000.0  # ms
        hz = 1000.0 / dt.mean()
        p50 = np.percentile(dt, 50)
        p95 = np.percentile(dt, 95)
        jitter = dt.std()
        print(f"{name:<20}{n:>8}{hz:>9.1f}{p50:>10.2f}{p95:>8.2f}{jitter:>8.2f}  {desc}")

    print("\n对照实验（另开终端，先 source scripts/env.sh）：")
    print("  ros2 topic hz /lowstate")
    print("  ros2 topic hz /lf/lowstate")
    print("  ros2 topic info /lowstate -v")
    print("\np95 远大于 p50，说明偶发卡顿；抖动大不一定是网络，也可能是回调里做的事太重。")
    print("如果 rt/lf/lowstate 一条都没有，先 ros2 topic list | grep lowstate 确认固件有没有发。")


if __name__ == "__main__":
    main()
