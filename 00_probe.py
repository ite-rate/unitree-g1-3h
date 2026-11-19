#!/usr/bin/env python3
"""00 连接自检：3 秒能收到多少条 rt/lowstate。

G1 把全身传感器的读数（IMU、每个电机的编码器/电流/温度、遥控器）打包成一条
LowState，每秒广播约 500 次。收得到，链路就通了；收不到，后面全部免谈。

用法（先 source scripts/env.sh）:
    python3 00_probe.py
"""
import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_

# 回调里只做最轻的事：计数、存最新一帧。解析放到主线程。
box = {"n": 0, "last": None}


def on_lowstate(msg: LowState_):
    box["n"] += 1
    box["last"] = msg


if __name__ == "__main__":
    ChannelFactoryInitialize(0)  # 网卡由 scripts/env.sh 里的 CYCLONEDDS_URI 决定
    sub = ChannelSubscriber("rt/lowstate", LowState_)
    sub.Init(on_lowstate, 10)   # 10 是接收队列长度
    print("订阅 rt/lowstate（unitree_hg），等 3 秒 ...")
    time.sleep(3.0)
    sub.Close()

    n, msg = box["n"], box["last"]
    if msg is None:
        print("\n[失败] 一条都没收到。按这个顺序查：")
        print("  1. 网线插了吗？ip addr 里有没有 192.168.123.x")
        print("  2. 机器人开机了吗？ping 192.168.123.161")
        print("  3. 这个终端 source scripts/env.sh 了吗？")
        print("  4. 机器人是不是被手机 App / 遥控器接管了？")
        print("  5. 连的是 G1 吗？G1 用 unitree_hg，Go2 用 unitree_go，消息类型不能混。")
        raise SystemExit(1)

    print(f"\n[通过] 收到 {n} 条，约 {n / 3:.0f} Hz")

    imu = msg.imu_state                      # 躯干里的 IMU
    r, p, y = imu.rpy
    print(f"姿态 roll/pitch/yaw   {r:+.3f} / {p:+.3f} / {y:+.3f} rad")
    print(f"角速度 gyroscope      {imu.gyroscope[0]:+.3f} rad/s（静止时接近 0）")

    legs = [msg.motor_state[i].q for i in range(12)]   # 0–11 是两条腿的编码器
    print(f"腿部 12 个关节角      {min(legs):+.3f} ~ {max(legs):+.3f} rad")

    taus = [abs(msg.motor_state[i].tau_est) for i in range(29)]   # 电机电流推算的力矩
    i_max = max(range(29), key=lambda i: taus[i])
    print(f"最大估计力矩          {taus[i_max]:.2f} N·m（{i_max} 号电机）")

    temps = [msg.motor_state[i].temperature[0] for i in range(29)]
    temps = [t for t in temps if t > 0]
    print(f"电机温度              {min(temps)} ~ {max(temps)} C" if temps
          else "电机温度              全 0：机器人可能还没上电")

    print(f"\ntick = {msg.tick}  （上电计数，每帧都在涨，说明数据是新的）")
    print("下一步: ros2 topic list —— 同一份数据在 ROS 2 里长什么样。")
