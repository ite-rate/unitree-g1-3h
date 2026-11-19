#!/usr/bin/env python3
"""05 G1 关节监视：把 /lowstate 里的 29 个关节读成人话。

每个关节就是一个电机，每个电机自带几样传感器，读数在 motor_state[i] 里：
    q 编码器测的关节角（rad）   dq 角速度   tau_est 电流推算的力矩
    temperature[0] 电机温度（C）

关节顺序（29 DOF）：0-11 腿，12-14 腰，15-21 左臂，22-28 右臂。
课堂演示：抬一下 G1 的手臂，看对应关节的 q 跟着变 —— 传感器 -> 数字，这就是感知。

用法:
    python3 05_joint_monitor.py                 # 全部关节，每秒刷新
    python3 05_joint_monitor.py --joint L_knee   # 只看一个关节
"""
import argparse
import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_

# 29 个关节的名字，按消息里的顺序。* 的槽位在 23 DOF 机型上无效。
NAMES = [
    "L_hip_pitch", "L_hip_roll", "L_hip_yaw", "L_knee", "L_ankle_pitch", "L_ankle_roll",
    "R_hip_pitch", "R_hip_roll", "R_hip_yaw", "R_knee", "R_ankle_pitch", "R_ankle_roll",
    "waist_yaw", "waist_roll*", "waist_pitch*",
    "L_shoulder_pitch", "L_shoulder_roll", "L_shoulder_yaw", "L_elbow",
    "L_wrist_roll", "L_wrist_pitch*", "L_wrist_yaw*",
    "R_shoulder_pitch", "R_shoulder_roll", "R_shoulder_yaw", "R_elbow",
    "R_wrist_roll", "R_wrist_pitch*", "R_wrist_yaw*",
]

box = {"last": None}


def on_lowstate(msg: LowState_):
    box["last"] = msg


def main():
    parser = argparse.ArgumentParser(description="监视 G1 的 29 个关节")
    parser.add_argument("--seconds", type=float, default=10.0, help="看多久；0 一直看")
    parser.add_argument("--joint", help="只看一个关节：编号 0-28 或名字，如 L_knee")
    args = parser.parse_args()

    if args.joint is not None:
        j = int(args.joint) if args.joint.isdigit() else \
            next((i for i, n in enumerate(NAMES) if n.lower() == args.joint.lower()), None)
        if j is None or not 0 <= j < 29:
            print(f"没有这个关节: {args.joint}")
            return
        indices = [j]
    else:
        indices = list(range(29))

    ChannelFactoryInitialize(0)
    sub = ChannelSubscriber("rt/lowstate", LowState_)
    sub.Init(on_lowstate, 10)
    print(f"订阅 rt/lowstate，{len(indices)} 个关节，每秒刷新（Ctrl+C 结束）...")

    try:
        t0 = time.monotonic()
        while args.seconds == 0 or time.monotonic() - t0 < args.seconds:
            time.sleep(1.0)
            msg = box["last"]
            if msg is None:
                print("  还没收到 /lowstate，先跑 00_probe.py 查链路。")
                continue
            rpy = msg.imu_state.rpy
            print(f"\n[t={time.monotonic() - t0:5.1f}s] roll/pitch/yaw = "
                  f"{rpy[0]:+.2f}/{rpy[1]:+.2f}/{rpy[2]:+.2f}")
            for i in indices:
                m = msg.motor_state[i]
                print(f"  {i:>2} {NAMES[i]:<18} q={m.q:+7.3f}  dq={m.dq:+7.3f}  "
                      f"tau={m.tau_est:+6.2f}  T={m.temperature[0]:>3} C")
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        sub.Close()

    print("提示：q 是关节角不是末端位置，末端位姿要自己做正运动学。")


if __name__ == "__main__":
    main()
