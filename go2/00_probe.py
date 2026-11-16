#!/usr/bin/env python3
# 附加章节：Go2 版本。保留原脚本，逻辑未改，只补了下面 3 行路径引导，
# 这样从 go2/ 目录直接运行时，也能 import 到仓库根目录的 unitree_sdk2py。
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
"""00 连接自检：我能不能"听见"机器人？

这是整节课最短的一步：只订阅 /lowstate，数一数 3 秒能收到多少条。
收到数据，后面的动作、灯、雷达、相机才有意义。

用法:
    python3 00_probe.py
    python3 00_probe.py --iface eth0
    python3 00_probe.py --seconds 5

这里没有任何课程封装：ChannelFactoryInitialize / ChannelSubscriber 就是
unitree_sdk2py 官方示例里的写法。
"""
import argparse
import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.unitree_go.msg.dds_ import LowState_


def main():
    parser = argparse.ArgumentParser(description="订阅 rt/lowstate，确认 DDS 链路")
    parser.add_argument("--iface", help="连机器人的网卡名，如 eth0；不填则用环境变量 CYCLONEDDS_URI")
    parser.add_argument("--seconds", type=float, default=3.0, help="观察多久（秒）")
    args = parser.parse_args()

    # domain 0 是 Unitree 默认值。网卡不填时，SDK 读 CYCLONEDDS_URI / 自动选网卡。
    if args.iface:
        ChannelFactoryInitialize(0, args.iface)
    else:
        ChannelFactoryInitialize(0)

    box = {"count": 0, "last": None}

    # 回调在 DDS 自己的线程里执行，这里只做最轻的计数和保存。
    def on_lowstate(msg: LowState_):
        box["count"] += 1
        box["last"] = msg

    sub = ChannelSubscriber("rt/lowstate", LowState_)
    sub.Init(on_lowstate, 10)  # 第二个参数是队列长度
    print(f"订阅 rt/lowstate，观察 {args.seconds:.0f} s ...")
    time.sleep(args.seconds)
    sub.Close()

    count, msg = box["count"], box["last"]
    if msg is None:
        print("\n[失败] 一条都没收到。按这个顺序查：")
        print("  1. 网线插了吗？ip addr 里有没有 192.168.123.x")
        print("  2. 机器人开机了吗？ping 192.168.123.161")
        print("  3. 当前终端 source scripts/env.sh 了吗？（CYCLONEDDS_URI 要指向连机器人的网卡）")
        print("  4. 机器人是不是被手机 App 或遥控器接管了？")
        return

    rpy = msg.imu_state.rpy
    temps = [msg.motor_state[i].temperature for i in range(12)]
    print("\n[通过] DDS 链路正常")
    print(f"  收到 {count} 条，约 {count / args.seconds:.0f} Hz")
    print(f"  电量 {msg.bms_state.soc}% | 电压 {msg.power_v:.2f} V | 电流 {msg.power_a:.2f} A")
    print(f"  姿态 roll/pitch/yaw = {rpy[0]:+.3f} / {rpy[1]:+.3f} / {rpy[2]:+.3f} rad")
    print(f"  12 个电机温度 {min(temps)}~{max(temps)} C")
    print("\n下一步: ros2 topic list，看看同一个 /lowstate 在 ROS 2 里长什么样。")


if __name__ == "__main__":
    main()
