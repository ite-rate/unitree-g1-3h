#!/usr/bin/env python3
# 附加章节：Go2 版本。保留原脚本，逻辑未改，只补了下面 3 行路径引导，
# 这样从 go2/ 目录直接运行时，也能 import 到仓库根目录的 unitree_sdk2py。
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
"""02 SDK 预设动作：让机器人打招呼、伸懒腰、跳舞。

这些动作不是我们写的控制算法，而是机器人固件里已经做好的"技能"。
SDK 只负责发一条 RPC 请求：rt/api/sport/request，带上 API 号（比如 Hello = 1016）。
机器人执行完，回一条 response，code = 0 表示成功。

用法:
    python3 02_actions.py --list
    python3 02_actions.py --action hello
    python3 02_actions.py --action dance1
    python3 02_actions.py --action walk        # 向前走 1 秒再停
    python3 02_actions.py --action demo        # 连做一串（真机演示用）
    python3 02_actions.py --action frontflip --allow-dangerous

安全:
    默认每条指令执行前都会停下来等你按回车。--yes 可跳过（仅限你已清场）。
    翻转/跳跃类动作必须加 --allow-dangerous，且要有垫子和保护人员。
"""
import argparse
import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.sport.sport_client import SportClient

# 名字, API 号, SDK 方法, 说明, 是否危险
# API 号来自 unitree_sdk2py/go2/sport/sport_api.py
ACTIONS = [
    ("balance",     1002, "BalanceStand",  "站稳（做其它动作前先来这个）", False),
    ("stand_up",    1004, "StandUp",       "从趴下站起来",                 False),
    ("stand_down",  1005, "StandDown",     "趴下",                         False),
    ("recovery",    1006, "RecoveryStand", "摔倒后恢复站立",               False),
    ("stop",        1003, "StopMove",      "停止移动",                     False),
    ("damp",        1001, "Damp",          "阻尼模式（会软下来）",         False),
    ("sit",         1009, "Sit",           "坐下",                         False),
    ("rise_sit",    1010, "RiseSit",       "从坐姿站起",                   False),
    ("hello",       1016, "Hello",         "抬手打招呼",                   False),
    ("stretch",     1017, "Stretch",       "伸懒腰",                       False),
    ("content",     1020, "Content",       "开心/满足动作",                False),
    ("dance1",      1022, "Dance1",        "跳舞 1",                       False),
    ("dance2",      1023, "Dance2",        "跳舞 2",                       False),
    ("heart",       1036, "Heart",         "比心",                         False),
    ("scrape",      1029, "Scrape",        "刨地",                         False),
    ("freewalk",    2045, "FreeWalk",      "自由行走模式",                 False),
    ("staticwalk",  1061, "StaticWalk",    "静态行走",                     False),
    ("trotrun",     1062, "TrotRun",       "小跑",                         False),
    ("frontflip",   1030, "FrontFlip",     "前空翻",                       True),
    ("frontjump",   1031, "FrontJump",     "前跳",                         True),
    ("frontpounce", 1032, "FrontPounce",   "前扑",                         True),
    ("leftflip",    2041, "LeftFlip",      "侧空翻",                       True),
    ("backflip",    2043, "BackFlip",      "后空翻",                       True),
]
BY_NAME = {row[0]: row for row in ACTIONS}

RPC_ERRORS = {
    3102: "请求没有发出去（网卡/DDS 配置问题）",
    3104: "等机器人回复超时（机器人没在听，或状态不允许）",
    3203: "机器人固件没有实现这个接口（型号/版本不支持）",
    3204: "参数不对",
}


def explain(code):
    print(f"  -> code = {code}")
    if code == 0:
        print("  成功。")
    elif code in RPC_ERRORS:
        print(f"  失败：{RPC_ERRORS[code]}")
    else:
        print("  失败：非 0。先检查机器人是否站立、是否被 App/遥控器接管。")


def main():
    parser = argparse.ArgumentParser(description="调用 Go2 的预设动作")
    parser.add_argument("--action", default="hello", help="动作名，见 --list")
    parser.add_argument("--list", action="store_true", help="列出所有动作")
    parser.add_argument("--iface", help="网卡名，如 eth0；不填则用 CYCLONEDDS_URI")
    parser.add_argument("--yes", action="store_true", help="跳过回车确认")
    parser.add_argument("--allow-dangerous", action="store_true", help="允许翻转/跳跃类动作")
    args = parser.parse_args()

    if args.list:
        print(f"{'名字':<14}{'API':<7}{'说明'}")
        for name, api_id, _, desc, dangerous in ACTIONS:
            mark = "  [危险]" if dangerous else ""
            print(f"{name:<14}{api_id:<7}{desc}{mark}")
        return

    if args.action != "demo" and args.action != "walk" and args.action not in BY_NAME:
        print(f"没有这个动作: {args.action}。用 --list 看全部。")
        return

    if args.action in BY_NAME and BY_NAME[args.action][4] and not args.allow_dangerous:
        print(f"{args.action} 属于翻转/跳跃动作。确认有垫子和保护人员后，加 --allow-dangerous。")
        return

    if not args.yes:
        print("即将向真机发送运动指令。")
        print("确认：场地清空、机器人周围 2 m 无人、手握急停。")
        input("按回车继续，Ctrl+C 取消: ")

    if args.iface:
        ChannelFactoryInitialize(0, args.iface)
    else:
        ChannelFactoryInitialize(0)

    client = SportClient()
    client.SetTimeout(10.0)
    client.Init()

    if args.action == "walk":
        print("Move(0.2, 0, 0)，走 1 秒，然后 StopMove()")
        try:
            client.Move(0.2, 0.0, 0.0)
            time.sleep(1.0)
        finally:
            explain(client.StopMove())
        return

    if args.action == "demo":
        # 演示顺序：先站稳，再做不会改变站姿的动作，最后停下。
        sequence = [("balance", 1.0), ("hello", 3.0), ("stretch", 3.0), ("dance1", 6.0)]
        try:
            for name, wait in sequence:
                _, api_id, method, desc, _ = BY_NAME[name]
                print(f"\n[{method}] API {api_id} - {desc}")
                explain(getattr(client, method)())
                time.sleep(wait)
        finally:
            print("\n[StopMove] 收尾")
            explain(client.StopMove())
        return

    _, api_id, method, desc, _ = BY_NAME[args.action]
    print(f"[{method}] API {api_id} - {desc}")
    explain(getattr(client, method)())


if __name__ == "__main__":
    main()
