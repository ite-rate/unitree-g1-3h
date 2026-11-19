#!/usr/bin/env python3
"""02 G1 运控：切状态机（FSM），让机器人站、蹲、坐、走、挥手。

G1 的运控不是"一个动作一个 API"，而是切状态机：
    client.SetFsmId(500)     进入主运控
    client.SetVelocity(...)  在主运控里给速度
SDK 里的 Damp() / Start() / Sit() 只是 SetFsmId(x) 的语法糖，
而且 Python 版这些语法糖不 return（拿不到 code），所以本脚本统一走 SetFsmId。

用法:
    python3 02_loco.py --list
    python3 02_loco.py --action start
    python3 02_loco.py --action move_forward
    python3 02_loco.py --demo
"""
import argparse
import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient

# 名字 -> (FSM ID, 说明)。ID 来源: g1_loco_api.py
FSM_ACTIONS = {
    "zero_torque":   (0,   "零力矩：关节立刻失去支撑，会软倒（危险）"),
    "damp":          (1,   "阻尼保护：关节变硬但不保持姿态"),
    "squat":         (2,   "蹲下"),
    "sit":           (3,   "坐下"),
    "stand_up":      (4,   "从坐/蹲站起"),
    "start":         (500, "进入主运控，之后才能移动 / 手臂动作"),
    "lie2standup":   (702, "从仰躺站起，要求仰面、硬平地（危险）"),
    "squat2standup": (706, "从蹲姿站起"),
}

# 不走 FSM 的动作，直接调对应方法
def do_action(client, name):
    if name in FSM_ACTIONS:
        fsm, desc = FSM_ACTIONS[name]
        print(f"SetFsmId({fsm})  # {desc}")
        return client.SetFsmId(fsm)
    if name == "high_stand":
        print("SetStandHeight(最高)")
        return client.SetStandHeight(0xFFFFFFFF)
    if name == "low_stand":
        print("SetStandHeight(最低)")
        return client.SetStandHeight(0)
    if name == "wave_hand":
        print("SetTaskId(0)  # 原地挥手")
        return client.SetTaskId(0)
    if name == "wave_hand_turn":
        print("SetTaskId(1)  # 转身挥手")
        return client.SetTaskId(1)
    if name == "shake_hand_start":
        print("SetTaskId(2)  # 伸手准备握手")
        return client.SetTaskId(2)
    if name == "shake_hand_end":
        print("SetTaskId(3)  # 结束握手")
        return client.SetTaskId(3)
    if name == "move_forward":
        print("SetVelocity(0.2, 0, 0) 走 1 秒")
        client.SetVelocity(0.2, 0.0, 0.0)
        time.sleep(1.0)
        return client.SetVelocity(0.0, 0.0, 0.0)
    if name == "move_lateral":
        print("SetVelocity(0, 0.2, 0) 左移 1 秒")
        client.SetVelocity(0.0, 0.2, 0.0)
        time.sleep(1.0)
        return client.SetVelocity(0.0, 0.0, 0.0)
    if name == "move_rotate":
        print("SetVelocity(0, 0, 0.3) 原地转 1 秒")
        client.SetVelocity(0.0, 0.0, 0.3)
        time.sleep(1.0)
        return client.SetVelocity(0.0, 0.0, 0.0)
    if name == "stop_move":
        print("SetVelocity(0, 0, 0)")
        return client.SetVelocity(0.0, 0.0, 0.0)
    raise ValueError(f"没有这个动作: {name}，用 --list 看全部")


def main():
    parser = argparse.ArgumentParser(description="调用 G1 的运控状态机 / 移动接口")
    parser.add_argument("--action", help="动作名，见 --list")
    parser.add_argument("--list", action="store_true", help="列出所有动作")
    parser.add_argument("--demo", action="store_true", help="按顺序做一小段演示")
    parser.add_argument("--yes", action="store_true", help="跳过回车确认（限已清场）")
    parser.add_argument("--allow-dangerous", action="store_true",
                        help="允许 zero_torque / lie2standup")
    args = parser.parse_args()

    if args.list:
        for name, (fsm, desc) in FSM_ACTIONS.items():
            print(f"{name:<16} FSM {fsm:<4} {desc}")
        for name, desc in [("high_stand", "站到最高"), ("low_stand", "站到最低"),
                           ("wave_hand", "原地挥手"), ("wave_hand_turn", "转身挥手"),
                           ("shake_hand_start", "伸手握手"), ("shake_hand_end", "结束握手"),
                           ("move_forward", "前进 0.2 m/s 1 秒"), ("move_lateral", "左移 1 秒"),
                           ("move_rotate", "原地转 1 秒"), ("stop_move", "速度清零")]:
            print(f"{name:<16} {'-':<4} {desc}")
        return

    if args.demo:
        names = ["damp", "start", "squat2standup", "wave_hand", "move_forward", "stop_move"]
    elif args.action:
        names = [args.action]
    else:
        print("要么 --list，要么 --action <名字>，要么 --demo")
        return

    if set(names) & {"zero_torque", "lie2standup"} and not args.allow_dangerous:
        print("zero_torque / lie2standup 会让机器人失去支撑或从躺姿起身。")
        print("确认地面平整、周围无人后，再加 --allow-dangerous。")
        return

    if not args.yes:
        print("即将向 G1 发送运控指令。确认：场地清空、周围 2 m 无人、手握急停。")
        input("按回车继续，Ctrl+C 取消: ")

    ChannelFactoryInitialize(0)
    client = LocoClient()
    client.SetTimeout(10.0)
    client.Init()

    try:
        for name in names:
            code = do_action(client, name)
            print(f"  -> code = {code}   （0 成功；非 0 先 damp、关 App，再重试）")
            time.sleep(1.0)
    finally:
        # 不管成功还是 Ctrl+C，最后都把速度清零。这条不能省。
        print("[收尾] SetVelocity(0,0,0) ->", client.SetVelocity(0.0, 0.0, 0.0))


if __name__ == "__main__":
    main()
