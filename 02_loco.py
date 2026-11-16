#!/usr/bin/env python3
"""02 G1 运控：站、蹲、坐、走、挥手，全部走 LocoClient。

G1 的运控不是"一个动作一个 API"，而是"切状态机（FSM）"：
    client.SetFsmId(500)   -> 进入主运控
    client.SetFsmId(706)   -> 从蹲姿站起
    client.SetVelocity(...)-> 在运控里给速度
SDK 里的 Damp() / Start() / Sit() 只是 SetFsmId(x) 的语法糖。

▶ 重要坑：Python 版这些语法糖（Damp/Start/Sit/...）都不 return，
  所以 `code = client.Damp()` 拿到的是 None。想看到返回码，就自己调
  `client.SetFsmId(x)`；本脚本为了打印 code，统一走 SetFsmId。

▶ 另一个坑：C++ 版有 Squat()=2、StandUp()=4，Python 版没包，
  所以这里直接用 SetFsmId(2) / SetFsmId(4)。

用法:
    python3 02_loco.py --list
    python3 02_loco.py --action start
    python3 02_loco.py --action squat2standup
    python3 02_loco.py --action move_forward
    python3 02_loco.py --demo
    python3 02_loco.py --action zero_torque --allow-dangerous   # 机器人会软倒

安全:
    默认每条指令执行前停下来等你按回车。--yes 可跳过（仅限已清场）。
    zero_torque / lie2standup 必须加 --allow-dangerous。
    所有移动类动作在 finally 里自动 StopMove。
"""
import argparse
import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient

# ▶ G1 运控动作表（课程主表）
# 名字 / FSM ID / 等价 SDK 调用 / 机器人做什么 / 风险
# FSM ID 来源：g1_loco_api.py + unitree_ros2 的 g1_loco_client.hpp
ACTIONS = [
    ("zero_torque",   0,   "SetFsmId(0)",   "零力矩：关节立刻失去支撑，机器人会软倒", "高"),
    ("damp",          1,   "Damp()",        "阻尼模式：关节变硬但不保持姿态，常用于保护", "低"),
    ("squat",         2,   "SetFsmId(2)",   "蹲下（Python 版没有 Squat() 封装）", "低"),
    ("sit",           3,   "Sit()",         "坐下", "低"),
    ("stand_up",      4,   "SetFsmId(4)",   "从坐/蹲站起（Python 版没有 StandUp() 封装）", "低"),
    ("start",         500, "Start()",       "进入主运控，后面才能 Move / 手臂动作", "低"),
    ("squat2standup", 706, "Squat2StandUp()", "从蹲姿站起", "低"),
    ("lie2standup",   702, "Lie2StandUp()", "从仰躺站起，要求仰面、硬平地", "高"),
    ("standup2squat", 706, "StandUp2Squat()", "蹲下（上游和 squat2standup 共用 706）", "低"),
]
BY_NAME = {row[0]: row for row in ACTIONS}

# 不走 FSM、走别的接口的动作：名字 / 说明 / 风险
OTHER_ACTIONS = [
    ("high_stand",     "站到最高（SetStandHeight=0xFFFFFFFF）", "低"),
    ("low_stand",      "站到最低（SetStandHeight=0）", "低"),
    ("wave_hand",      "原地挥手（SetTaskId=0）", "低"),
    ("wave_hand_turn", "转身挥手（SetTaskId=1）", "中"),
    ("shake_hand_start", "伸手准备握手（SetTaskId=2）", "中"),
    ("shake_hand_end",   "结束握手（SetTaskId=3）", "中"),
    ("move_forward",   "前进 0.2 m/s，1 秒后自动停", "中"),
    ("move_lateral",   "左移 0.2 m/s，1 秒后自动停", "中"),
    ("move_rotate",    "原地转 0.3 rad/s，1 秒后自动停", "中"),
    ("stop_move",      "速度清零（SetVelocity 0,0,0）", "低"),
]
OTHER_BY_NAME = {row[0]: row for row in OTHER_ACTIONS}

DANGEROUS = {"zero_torque", "lie2standup"}

RPC_ERRORS = {
    3102: "请求没有发出去（网卡 / DDS 配置问题）",
    3104: "等机器人回复超时（机器人没在听，或当前状态不允许）",
    3203: "机器人固件没有实现这个接口（型号 / 版本不支持）",
    3204: "参数不对",
    7301: "LocoState 不可用：运控服务还没起来",
    7302: "FSM ID 非法：这个机型不支持该状态",
    7303: "Task ID 非法：挥手 / 握手的参数不对",
}


def explain(code):
    print(f"  -> code = {code}")
    if code == 0:
        print("  成功。")
    elif code in RPC_ERRORS:
        print(f"  失败：{RPC_ERRORS[code]}")
    else:
        print("  失败：非 0。先确认机器人站立、没被 App/遥控器接管，再重试。")


def call_action(client, name):
    """执行一个动作，返回 (code, 说明)。code=None 表示上游封装没返回。"""
    if name in BY_NAME:
        _, fsm, call, desc, _ = BY_NAME[name]
        print(f"[{call}] FSM {fsm} - {desc}")
        return client.SetFsmId(fsm), desc

    if name == "high_stand":
        return client.SetStandHeight(0xFFFFFFFF), "站到最高"
    if name == "low_stand":
        return client.SetStandHeight(0), "站到最低"
    if name == "wave_hand":
        return client.SetTaskId(0), "原地挥手"
    if name == "wave_hand_turn":
        return client.SetTaskId(1), "转身挥手"
    if name == "shake_hand_start":
        return client.SetTaskId(2), "开始握手"
    if name == "shake_hand_end":
        return client.SetTaskId(3), "结束握手"
    if name == "stop_move":
        return client.SetVelocity(0.0, 0.0, 0.0), "速度清零"

    if name in ("move_forward", "move_lateral", "move_rotate"):
        vx, vy, vyaw = {
            "move_forward": (0.2, 0.0, 0.0),
            "move_lateral": (0.0, 0.2, 0.0),
            "move_rotate": (0.0, 0.0, 0.3),
        }[name]
        print(f"[Move] vx={vx} vy={vy} vyaw={vyaw}，持续 1 s")
        client.Move(vx, vy, vyaw)  # 注意：Move() 也不返回 code
        time.sleep(1.0)
        return client.SetVelocity(0.0, 0.0, 0.0), "走 1 秒后停下"

    raise ValueError(f"unknown action: {name}")


def print_list():
    print(f"{'名字':<18}{'FSM':<6}{'触发':<20}{'说明':<44}风险")
    print("-" * 100)
    for name, fsm, call, desc, risk in ACTIONS:
        mark = "  [危险]" if risk == "高" else ""
        print(f"{name:<18}{fsm:<6}{call:<20}{desc:<44}{risk}{mark}")
    for name, desc, risk in OTHER_ACTIONS:
        mark = "  [危险]" if risk == "高" else ""
        print(f"{name:<18}{'-':<6}{'见说明':<20}{desc:<44}{risk}{mark}")


def main():
    parser = argparse.ArgumentParser(description="调用 G1 的运控状态机 / 移动接口")
    parser.add_argument("--action", help="动作名，见 --list")
    parser.add_argument("--list", action="store_true", help="列出所有动作")
    parser.add_argument("--demo", action="store_true", help="按顺序做一小段演示")
    parser.add_argument("--iface", help="网卡名，如 eth0；不填则用 CYCLONEDDS_URI")
    parser.add_argument("--yes", action="store_true", help="跳过回车确认")
    parser.add_argument("--allow-dangerous", action="store_true", help="允许 zero_torque / lie2standup")
    args = parser.parse_args()

    if args.list:
        print_list()
        return

    if args.demo:
        sequence = ["damp", "start", "squat2standup", "wave_hand", "move_forward", "stop_move"]
    elif args.action:
        sequence = [args.action]
    else:
        print("要么 --list，要么 --action <名字>，要么 --demo。例如：")
        print("  python3 02_loco.py --list")
        print("  python3 02_loco.py --action start")
        return

    unknown = [n for n in sequence if n not in BY_NAME and n not in OTHER_BY_NAME]
    if unknown:
        print(f"没有这个动作: {', '.join(unknown)}。用 --list 看全部。")
        return

    need_danger = [n for n in sequence if n in DANGEROUS]
    if need_danger and not args.allow_dangerous:
        print(f"{', '.join(need_danger)} 会让机器人失去支撑或从躺姿起身。")
        print("确认地面平整、周围无人后，再加 --allow-dangerous。")
        return

    if not args.yes:
        print("即将向 G1 发送运控指令。")
        print("确认：场地清空、机器人周围 2 m 无人、手握急停。")
        input("按回车继续，Ctrl+C 取消: ")

    if args.iface:
        ChannelFactoryInitialize(0, args.iface)
    else:
        ChannelFactoryInitialize(0)

    client = LocoClient()
    client.SetTimeout(10.0)
    client.Init()

    try:
        if args.demo:
            waits = {"damp": 0.5, "start": 1.0, "squat2standup": 2.0,
                     "wave_hand": 2.0, "move_forward": 0.0, "stop_move": 0.0}
            for name in sequence:
                code, _ = call_action(client, name)
                explain(code)
                time.sleep(waits.get(name, 1.0))
            print("\ndemo 结束。")
        else:
            explain(call_action(client, sequence[0])[0])
    finally:
        # 不管上面成功还是 Ctrl+C，最后都把速度清零。
        print("\n[收尾] SetVelocity(0,0,0)")
        explain(client.SetVelocity(0.0, 0.0, 0.0))


if __name__ == "__main__":
    main()
