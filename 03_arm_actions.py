#!/usr/bin/env python3
"""03 G1 手臂动作：一调用就做的 16 个预置动作。

接口是 G1ArmActionClient，每个动作只发一个整数 action_id，
轨迹在机器人固件里已经编好。名字和编号直接用 SDK 自带的 action_map。

两个要点：
    - 保持型动作（举手、比心、握手…）做完不会自动收回，脚本会补一条 99 释放；
    - 手臂动作只在 FSM 500 / 501 / 801 下可用，返回 7404 就先跑 02_loco.py --action start。

用法:
    python3 03_arm_actions.py --list
    python3 03_arm_actions.py --action "high wave"
    python3 03_arm_actions.py --demo
"""
import argparse
import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.arm.g1_arm_action_client import G1ArmActionClient, action_map
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient

# 做完不自动收回的动作（做完默认补一条 release arm）
HOLDING = {"hands up", "high five", "hug", "heart", "right heart", "shake hand"}


def main():
    parser = argparse.ArgumentParser(description="调用 G1 的手臂预置动作")
    parser.add_argument("--action", help="动作名，见 --list（就是 SDK action_map 的键）")
    parser.add_argument("--list", action="store_true", help="列出所有动作")
    parser.add_argument("--demo", action="store_true", help="挥手 -> 拍手 -> 比心 -> 释放")
    parser.add_argument("--yes", action="store_true", help="跳过回车确认")
    args = parser.parse_args()

    if args.list:
        for name, action_id in action_map.items():
            mark = "  (保持型)" if name in HOLDING else ""
            print(f"{action_id:>3}  {name}{mark}")
        return

    if args.demo:
        names = ["high wave", "clap", "heart", "release arm"]
    elif args.action:
        if args.action not in action_map:
            print(f"没有这个动作: {args.action}。用 --list 看全部（名字要和 action_map 完全一致）。")
            return
        names = [args.action]
    else:
        print("要么 --list，要么 --action <名字>，要么 --demo")
        return

    if not args.yes:
        print("即将让 G1 做手臂动作。确认：手臂活动范围内没人、没桌子，手握急停。")
        input("按回车继续，Ctrl+C 取消: ")

    ChannelFactoryInitialize(0)

    # 先查一次 FSM：手臂动作只认 500 / 501 / 801，把 7404 提前讲清楚
    loco = LocoClient()
    loco.SetTimeout(5.0)
    loco.Init()
    code, fsm_id = loco.GetFsmId()
    if code == 0:
        print(f"当前 FSM = {fsm_id}" +
              ("（可以）" if fsm_id in (500, 501, 801) else "  <- 先跑 02_loco.py --action start"))

    arm = G1ArmActionClient()
    arm.SetTimeout(10.0)
    arm.Init()

    try:
        for name in names:
            action_id = action_map[name]
            print(f'ExecuteAction({action_id})  # {name}')
            print("  ->", arm.ExecuteAction(action_id), "（0 成功；7404=先 start，7401=先 release）")
            time.sleep(2.0)
            if name in HOLDING:
                print('ExecuteAction(99)  # release arm（保持型动作的收尾）')
                arm.ExecuteAction(action_map["release arm"])
                time.sleep(1.0)
    finally:
        print("[收尾] release arm (99) ->", arm.ExecuteAction(action_map["release arm"]))


if __name__ == "__main__":
    main()
