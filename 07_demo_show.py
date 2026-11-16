#!/usr/bin/env python3
"""07 综合演示：一条命令把今天的东西串起来。

流程（真机演示顺序）：
    1. 读 /lowstate：姿态、关节温度
    2. 灯带变蓝，音量调到 80
    3. TTS 开场
    4. 进入运控（FSM 500）-> 从蹲姿站起（FSM 706）
    5. 挥手（Task 0）
    6. 手臂动作 high wave（ID 26）-> 99 释放
    7. 前进 0.2 m/s，1 秒后停（--no-walk 可跳过）
    8. 坐下（FSM 3）-> 灯灭 -> TTS 结束

安全：默认会停下来等你确认。请清场、留出 2 m、手握急停。
      任何一步失败都继续往下走，最后统一 StopMove + 释放手臂。

用法:
    python3 07_demo_show.py
    python3 07_demo_show.py --yes
    python3 07_demo_show.py --iface eth0 --no-walk
"""
import argparse
import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.g1.arm.g1_arm_action_client import G1ArmActionClient, action_map
from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_

G1_MOTOR_COUNT = 29


def stage(text):
    print(f"\n===== {text} =====")


def read_status(seconds=2.0):
    box = {"msg": None}
    sub = ChannelSubscriber("rt/lowstate", LowState_)
    sub.Init(lambda m: box.__setitem__("msg", m), 10)
    time.sleep(seconds)
    sub.Close()

    msg = box["msg"]
    if msg is None:
        print("没有收到 /lowstate，先跑 00_probe.py 排障。")
        return False

    temps = [msg.motor_state[i].temperature[0] for i in range(G1_MOTOR_COUNT)]
    temps = [t for t in temps if t > 0]
    temp_text = f"{min(temps)}~{max(temps)} C" if temps else "全 0（待机？）"
    print(f"mode_machine={msg.mode_machine} | tick={msg.tick}")
    print(f"roll/pitch/yaw = {msg.imu_state.rpy[0]:+.2f} / {msg.imu_state.rpy[1]:+.2f} / {msg.imu_state.rpy[2]:+.2f} rad")
    print(f"电机温度 {temp_text}")
    return True


def show(code, label):
    print(f"{label:<28} code={code}")
    return code


def main():
    parser = argparse.ArgumentParser(description="G1 三小时课程综合演示")
    parser.add_argument("--iface", help="网卡名，如 eth0；不填则用 CYCLONEDDS_URI")
    parser.add_argument("--yes", action="store_true", help="跳过回车确认")
    parser.add_argument("--no-walk", action="store_true", help="跳过前进那一步")
    args = parser.parse_args()

    if not args.yes:
        print("即将让 G1 做动作：站起、挥手、手臂动作、前进、坐下。")
        print("确认：场地清空、周围 2 m 无人、手握急停。")
        input("按回车开始，Ctrl+C 取消: ")

    if args.iface:
        ChannelFactoryInitialize(0, args.iface)
    else:
        ChannelFactoryInitialize(0)

    loco = LocoClient()
    loco.SetTimeout(10.0)
    loco.Init()

    audio = AudioClient()
    audio.SetTimeout(10.0)
    audio.Init()

    arm = G1ArmActionClient()
    arm.SetTimeout(10.0)
    arm.Init()

    try:
        stage("1. 读状态")
        if not read_status():
            return

        stage("2. 灯与音量")
        show(audio.LedControl(0, 0, 255), "LedControl(0,0,255)")
        show(audio.SetVolume(80), "SetVolume(80)")

        stage("3. 开场语音")
        show(audio.TtsMaker("大家好，我是宇树 G1。接下来演示运控、手臂和语音。", 0), "TtsMaker")
        time.sleep(4.0)

        stage("4. 运控：进入主运控 -> 站起")
        show(loco.SetFsmId(500), "SetFsmId(500) = Start")
        time.sleep(1.0)
        show(loco.SetFsmId(706), "SetFsmId(706) = Squat2StandUp")
        time.sleep(3.0)

        stage("5. 挥手")
        show(loco.SetTaskId(0), "SetTaskId(0) = WaveHand")
        time.sleep(3.0)

        stage("6. 手臂动作")
        show(arm.ExecuteAction(action_map["high wave"]), "ExecuteAction(26) high wave")
        time.sleep(3.0)
        show(arm.ExecuteAction(action_map["release arm"]), "ExecuteAction(99) release")

        stage("7. 前进")
        if args.no_walk:
            print("跳过（--no-walk）")
        else:
            # SetVelocity 的 duration=1.0 表示"以这个速度走 1 秒"，比 Move() 更直观。
            show(loco.SetVelocity(0.2, 0.0, 0.0, 1.0), "SetVelocity(0.2,0,0,1s)")
            time.sleep(1.5)
            show(loco.SetVelocity(0.0, 0.0, 0.0), "SetVelocity(0,0,0)")

        stage("8. 坐下")
        show(loco.SetFsmId(3), "SetFsmId(3) = Sit")
        time.sleep(2.0)

        stage("9. 收尾")
        show(audio.LedControl(0, 0, 0), "LedControl(0,0,0)")
        show(audio.TtsMaker("演示结束，谢谢大家。", 0), "TtsMaker")

    finally:
        stage("10. 安全收尾")
        print("SetVelocity(0,0,0):", loco.SetVelocity(0.0, 0.0, 0.0))
        print("release arm (99):  ", arm.ExecuteAction(action_map["release arm"]))
        print("LedControl(0,0,0):  ", audio.LedControl(0, 0, 0))
        print("\n演示结束。")


if __name__ == "__main__":
    main()
