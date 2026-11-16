#!/usr/bin/env python3
"""00 连接自检：我能不能"听见"G1？

整节课最短的一步：只订阅 /lowstate，数一数 3 秒能收到多少条。
收到数据，后面的运控、手臂、语音、关节才有意义。

G1 和 Go2 最大的区别在消息类型：
    Go2 -> unitree_go.msg.LowState   （12 个电机，带电池）
    G1  -> unitree_hg.msg.LowState   （35 个电机槽位，不带电池）
本文件用的是 unitree_hg，这是 G1 的官方 IDL。

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
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_

# G1 29 DOF 机型：0–28 是有效关节，29–34 是消息里预留的槽位。
# 23 DOF 机型只有其中一部分；所以下面统一只统计 temperature > 0 的槽位。
G1_MOTOR_COUNT = 29
LEG_JOINTS = 12


def main():
    parser = argparse.ArgumentParser(description="订阅 rt/lowstate，确认 G1 的 DDS 链路")
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
    print(f"订阅 rt/lowstate（unitree_hg），观察 {args.seconds:.0f} s ...")
    time.sleep(args.seconds)
    sub.Close()

    count, msg = box["count"], box["last"]
    if msg is None:
        print("\n[失败] 一条都没收到。按这个顺序查：")
        print("  1. 网线插了吗？ip addr 里有没有 192.168.123.x")
        print("  2. 机器人开机了吗？ping 192.168.123.161")
        print("  3. 当前终端 source scripts/env.sh 了吗？（CYCLONEDDS_URI 要指向连机器人的网卡）")
        print("  4. 机器人是不是被手机 App 或遥控器接管了？")
        print("  5. 你连的到底是 G1 吗？G1 用 unitree_hg，Go2 用 unitree_go，消息类型不能混。")
        return

    rpy = msg.imu_state.rpy
    # temperature 是 int16[2]：两个绕组/传感器的温度，课堂只看第 0 个。
    temps = [msg.motor_state[i].temperature[0] for i in range(G1_MOTOR_COUNT)]
    temps = [t for t in temps if t > 0]
    legs = [msg.motor_state[i].q for i in range(LEG_JOINTS)]

    print("\n[通过] DDS 链路正常")
    print(f"  收到 {count} 条，约 {count / args.seconds:.0f} Hz")
    print(f"  mode_machine = {msg.mode_machine}（机型/自由度编号）  mode_pr = {msg.mode_pr}（0=PR 串联 1=AB 并联）")
    print(f"  tick = {msg.tick}（机器人上电后的控制计数）")
    print(f"  姿态 roll/pitch/yaw = {rpy[0]:+.3f} / {rpy[1]:+.3f} / {rpy[2]:+.3f} rad")
    print(f"  腿部 12 个关节 q = {min(legs):+.3f} ~ {max(legs):+.3f} rad")
    if temps:
        print(f"  {len(temps)} 个电机温度 {min(temps)}~{max(temps)} C")
    else:
        print("  电机温度全是 0：先确认机器人已上电、且不是低功耗待机状态")
    print("\n注意：G1 的 LowState 里没有电池字段（Go2 才有 bms_state），电量看 App。")
    print("下一步: ros2 topic list，看看同一个 /lowstate 在 ROS 2 里长什么样。")


if __name__ == "__main__":
    main()
