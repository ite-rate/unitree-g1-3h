#!/usr/bin/env python3
"""00 连接自检：G1 身上的传感器，数据能不能到我的电脑？

先建立一个概念：机器人身上所有"读出来的数"，都来自某个传感器。
G1 把好几类传感器的读数，打包成一条消息 LowState，每秒发约 500 次。
所以每收到一帧，就等于拿到了这些传感器在同一时刻的一张快照：

    传感器                 测什么                      在 LowState 里叫
    IMU（躯干里）          姿态、角速度、加速度          imu_state
    关节编码器（每个电机）  关节角度、角速度              motor_state[i].q / dq
    电机电流（每个电机）    推算出来的力矩                motor_state[i].tau_est
    温度传感器（每个电机）  电机温度                      motor_state[i].temperature
    遥控器                 按键、摇杆                    wireless_remote

G1 头部还有两个"看环境"的传感器，数据不在 LowState 里，单独看：
    激光雷达 MID-360S      周围一圈物体的距离（点云）    08_lidar.py（要先启动雷达驱动）
    深度相机 D435i         彩色图 + 每个像素的距离       09_depth_camera.py
上面五类测的都是机器人"自己"，这两个测的是"周围的环境"。电池走单独的 BMS 消息，本课不展开。

本脚本做两件事：
    1. 数 3 秒收到几条：收不到，后面都免谈；
    2. 收到了，就按"传感器"分组，把最后一帧打印出来。

用法:
    python3 00_probe.py
    python3 00_probe.py --iface eth0
    python3 00_probe.py --seconds 5

这里没有任何课程封装：ChannelFactoryInitialize / ChannelSubscriber 就是
unitree_sdk2py 官方示例里的写法。G1 用 unitree_hg 消息，Go2 用 unitree_go，不能混。
"""
import argparse
import math
import struct
import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_

# G1 29 DOF 机型：0–28 是有效关节，29–34 是消息里预留的槽位。
G1_MOTOR_COUNT = 29
LEG_JOINTS = range(12)  # 0–11 是两条腿


def print_by_sensor(msg):
    """把一帧 LowState 按传感器分组打印。每一组对应机器人身上一类真实的传感器。"""
    motors = [msg.motor_state[i] for i in range(G1_MOTOR_COUNT)]

    # ① IMU：装在躯干里，测的是"身体"的运动，不是某个关节的。
    imu = msg.imu_state
    r, p, y = imu.rpy
    gx, gy, gz = imu.gyroscope
    acc = math.sqrt(sum(a * a for a in imu.accelerometer))
    print("① IMU（躯干里的惯性测量单元）")
    print(f"     姿态 roll/pitch/yaw   {r:+.3f} / {p:+.3f} / {y:+.3f} rad")
    print(f"     角速度（陀螺仪）      {gx:+.3f} / {gy:+.3f} / {gz:+.3f} rad/s")
    print(f"     加速度大小（加速度计） {acc:.2f} m/s²   静止时约 9.8，测到的就是重力")

    # ② 关节编码器：每个电机上一个，测这个关节转到了多少度、转得多快。
    legs = [motors[i].q for i in LEG_JOINTS]
    print("② 关节编码器（每个电机一个）")
    print(f"     腿部 12 个关节角 q    {min(legs):+.3f} ~ {max(legs):+.3f} rad")
    print("     每个关节的细节，见 05_joint_monitor.py")

    # ③ 力矩：tau_est 不是力矩传感器直接测的，是由电机电流推算出来的估计值。
    i_max = max(range(G1_MOTOR_COUNT), key=lambda i: abs(motors[i].tau_est))
    print("③ 电机电流 -> 估计力矩")
    print(f"     最大 |tau_est|        {abs(motors[i_max].tau_est):.2f} N·m（{i_max} 号电机）")

    # ④ 温度：每个电机两路，课堂只看第 0 路。全是 0 通常说明电机没上电。
    temps = [m.temperature[0] for m in motors if m.temperature[0] > 0]
    print("④ 电机温度传感器")
    if temps:
        print(f"     {len(temps)} 个电机        {min(temps)} ~ {max(temps)} C")
    else:
        print("     全是 0：先确认机器人已上电，且不是低功耗待机")

    # ⑤ 遥控器：40 字节原始数据，按键和摇杆都在里面（解析方法见 utils/joystick.py）。
    raw = bytes(msg.wireless_remote)
    lx = struct.unpack("f", raw[4:8])[0]
    ly = struct.unpack("f", raw[20:24])[0]
    print("⑤ 遥控器")
    print(f"     左摇杆 lx / ly        {lx:+.2f} / {ly:+.2f}   遥控器没连时为 0")

    print(f"\n   tick = {msg.tick}（上电后的计数，每帧都在涨，说明数据是新的）")


def main():
    parser = argparse.ArgumentParser(description="订阅 rt/lowstate，确认 G1 的传感器数据能收到")
    parser.add_argument("--iface", help="连机器人的网卡名，如 eth0；不填则用环境变量 CYCLONEDDS_URI")
    parser.add_argument("--seconds", type=float, default=3.0, help="观察多久（秒）")
    args = parser.parse_args()

    # domain 0 是 Unitree 默认值。网卡不填时，SDK 读 CYCLONEDDS_URI / 自动选网卡。
    if args.iface:
        ChannelFactoryInitialize(0, args.iface)
    else:
        ChannelFactoryInitialize(0)

    box = {"count": 0, "last": None}

    # 回调只做最轻的事：计数，保存最新一帧。解析和打印放到最后，在主线程里做。
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

    print(f"\n[通过] 收到 {count} 条，约 {count / args.seconds:.0f} Hz")
    print(f"机型 mode_machine = {msg.mode_machine}，踝关节 mode_pr = {msg.mode_pr}（0=PR 串联 1=AB 并联）\n")
    print("最后一帧，按传感器分组：")
    print_by_sensor(msg)

    print("\n电池不在 LowState 里（Go2 才把电池放在 LowState），电量看 App。")
    print("头部的激光雷达和深度相机也不在这里：见 08_lidar.py、09_depth_camera.py。")
    print("下一步: ros2 topic list，看看同一个 /lowstate 在 ROS 2 里长什么样。")


if __name__ == "__main__":
    main()
