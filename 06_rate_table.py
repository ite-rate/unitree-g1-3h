#!/usr/bin/env python3
"""06 频率与抖动：数据多久来一次、来得稳不稳。

G1 把同一份整机状态按两种频率广播：
    rt/lowstate      高频（约 500 Hz），低层控制用
    rt/lf/lowstate   低频（约 50 Hz），看状态 / 记日志用

间隔的 p95 远大于 p50，说明偶发卡顿；抖动是间隔的标准差。
对照：ros2 topic hz /lowstate 应该和脚本数字接近。

用法:
    python3 06_rate_table.py --seconds 10
"""
import argparse
import time

import numpy as np

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_

TOPICS = ["rt/lowstate", "rt/lf/lowstate"]

# 每个 topic 一份：{收到时刻的列表}
times = {name: [] for name in TOPICS}


def make_handler(name):
    def handler(_msg):
        times[name].append(time.monotonic())
    return handler


def main():
    parser = argparse.ArgumentParser(description="对比 G1 两路 /lowstate 的频率与抖动")
    parser.add_argument("--seconds", type=float, default=10.0, help="统计时长")
    args = parser.parse_args()

    ChannelFactoryInitialize(0)
    subs = []
    for name in TOPICS:
        sub = ChannelSubscriber(name, LowState_)
        sub.Init(make_handler(name), 10)
        subs.append(sub)

    print(f"统计 {args.seconds:.0f} 秒 ...")
    time.sleep(args.seconds)
    for sub in subs:
        sub.Close()

    print(f"\n{'topic':<20}{'条数':>8}{'Hz':>8}{'间隔p50':>9}{'p95':>8}{'抖动':>8}")
    print("-" * 61)
    for name in TOPICS:
        t = np.array(times[name])
        if t.size < 2:
            print(f"{name:<20}{t.size:>8}{'-':>8}{'-':>9}{'-':>8}{'-':>8}")
            continue
        dt = np.diff(t) * 1000.0   # 间隔，毫秒
        print(f"{name:<20}{t.size:>8}{1000 / dt.mean():>8.1f}"
              f"{np.percentile(dt, 50):>9.2f}{np.percentile(dt, 95):>8.2f}{dt.std():>8.2f}")

    print("\n对照（另开终端，先 source scripts/env.sh）：")
    print("  ros2 topic hz /lowstate")
    print("  ros2 topic hz /lf/lowstate")


if __name__ == "__main__":
    main()
