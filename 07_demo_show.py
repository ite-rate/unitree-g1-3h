#!/usr/bin/env python3
"""07 综合演示：一条命令把今天的东西串起来。

顺序：灯蓝 + 音量 -> TTS 开场 -> 进主运控 -> 蹲姿站起 -> 挥手
      -> 手臂 high wave -> 释放 -> 前进 1 秒 -> 坐下 -> 灯灭 -> TTS 结束。
任何一步失败都继续往下走，finally 里统一停机 + 释放手臂。

用法:
    python3 07_demo_show.py
    python3 07_demo_show.py --yes --no-walk
"""
import argparse
import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.arm.g1_arm_action_client import G1ArmActionClient, action_map
from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient


def main():
    parser = argparse.ArgumentParser(description="G1 三小时课程综合演示")
    parser.add_argument("--yes", action="store_true", help="跳过回车确认")
    parser.add_argument("--no-walk", action="store_true", help="跳过前进那一步")
    args = parser.parse_args()

    if not args.yes:
        print("即将让 G1 站起、挥手、走一步、坐下。确认：场地清空、周围 2 m 无人、手握急停。")
        input("按回车开始，Ctrl+C 取消: ")

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
        print("灯蓝 + 音量 80:", audio.LedControl(0, 0, 255), audio.SetVolume(80))
        print("TTS 开场:", audio.TtsMaker("大家好，我是宇树 G1。", 0))
        time.sleep(4.0)

        print("SetFsmId(500) 进主运控:", loco.SetFsmId(500))
        time.sleep(1.0)
        print("SetFsmId(706) 蹲姿站起:", loco.SetFsmId(706))
        time.sleep(3.0)

        print("SetTaskId(0) 挥手:", loco.SetTaskId(0))
        time.sleep(3.0)

        print("手臂 high wave:", arm.ExecuteAction(action_map["high wave"]))
        time.sleep(3.0)
        print("释放手臂:", arm.ExecuteAction(action_map["release arm"]))

        if not args.no_walk:
            print("前进 1 秒:", loco.SetVelocity(0.2, 0.0, 0.0, 1.0))
            time.sleep(1.5)
            print("停止:", loco.SetVelocity(0.0, 0.0, 0.0))

        print("SetFsmId(3) 坐下:", loco.SetFsmId(3))
        time.sleep(2.0)
        print("灯灭 + 结束语:", audio.LedControl(0, 0, 0),
              audio.TtsMaker("演示结束，谢谢大家。", 0))
    finally:
        print("\n[安全收尾]")
        print("SetVelocity(0,0,0):", loco.SetVelocity(0.0, 0.0, 0.0))
        print("release arm (99): ", arm.ExecuteAction(action_map["release arm"]))
        print("LedControl(0,0,0): ", audio.LedControl(0, 0, 0))


if __name__ == "__main__":
    main()
