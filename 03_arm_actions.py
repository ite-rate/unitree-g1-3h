#!/usr/bin/env python3
"""03 G1 手臂动作：16 个"一调用就做"的预置动作。

接口是 G1ArmActionClient，服务名 "arm"，底层 topic 是 rt/api/arm/request。
每个动作只发一个整数 action_id，机器人固件里已经编好了轨迹。

▶ 动作枚举（action_id 来自 g1_arm_action_client.py 的 action_map）
    99  release arm     释放/收回手臂，所有"保持型"动作的收尾
    11  two-hand kiss   双手飞吻
    12  left kiss       左手飞吻
    13  right kiss      右手飞吻
    15  hands up        双手举起（保持型，重心会变）
    17  clap            拍手
    18  high five       举手击掌（保持型）
    19  hug             拥抱姿势（保持型）
    20  heart           比心（保持型）
    21  right heart     右手比心（保持型）
    22  reject          拒绝手势
    23  right hand up   举右手
    24  x-ray           双手交叉成 X
    25  face wave       脸旁挥手
    26  high wave       高举挥手
    27  shake hand      握手（保持型）

▶ 保持型动作（15/18/19/20/21/27）做完不会自动收回手臂，
  默认在本脚本里补一条 99（release arm）；想保持就加 --hold。

▶ 手臂动作只在 FSM 500 / 501 / 801 下可用（错误码 7404）。
  脚本执行前会用 LocoClient.GetFsmId() 查一次，不在范围就提示先跑
  `python3 02_loco.py --action start`。

用法:
    python3 03_arm_actions.py --list
    python3 03_arm_actions.py --action "high wave"
    python3 03_arm_actions.py --action "heart"
    python3 03_arm_actions.py --id 27
    python3 03_arm_actions.py --demo
"""
import argparse
import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.arm.g1_arm_action_client import G1ArmActionClient, action_map
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient

# 名字 / action_id / 中文说明 / 是否保持型 / 风险
ARMS = [
    ("release arm",   99, "释放/收回手臂，保持型动作的收尾", False, "低"),
    ("two-hand kiss", 11, "双手飞吻", False, "低"),
    ("left kiss",     12, "左手飞吻", False, "低"),
    ("right kiss",    13, "右手飞吻", False, "低"),
    ("hands up",      15, "双手举起（重心会变）", True, "中"),
    ("clap",          17, "拍手", False, "低"),
    ("high five",     18, "举手击掌", True, "中"),
    ("hug",           19, "拥抱姿势", True, "中"),
    ("heart",         20, "比心", True, "中"),
    ("right heart",   21, "右手比心", True, "中"),
    ("reject",        22, "拒绝手势", False, "低"),
    ("right hand up", 23, "举右手", False, "低"),
    ("x-ray",         24, "双手交叉成 X", False, "低"),
    ("face wave",     25, "脸旁挥手", False, "低"),
    ("high wave",     26, "高举挥手", False, "低"),
    ("shake hand",    27, "握手", True, "中"),
]
BY_NAME = {row[0]: row for row in ARMS}
BY_ID = {row[1]: row for row in ARMS}

SUPPORTED_FSM = {500, 501, 801}

ARM_ERRORS = {
    7400: "rt/armsdk 被占用：别的同时在控手臂的进程关掉",
    7401: "手臂正持有上一个动作：先发 99 release arm，或重复同一动作",
    7402: "action_id 非法：用 --list 看可用值",
    7404: "当前 FSM 不支持手臂动作：先 02_loco.py --action start（FSM 500/501/801）",
    3102: "请求没发出去（网卡 / DDS 配置）",
    3104: "等回复超时（机器人没在听，或当前状态不允许）",
}


def explain(code):
    print(f"  -> code = {code}")
    if code == 0:
        print("  成功。")
    elif code in ARM_ERRORS:
        print(f"  失败：{ARM_ERRORS[code]}")
    else:
        print("  失败：非 0。先确认 FSM 在 500/501/801，且没有别的进程控手臂。")


def print_list():
    print(f"{'名字':<16}{'ID':<6}{'说明':<36}{'保持型':<8}风险")
    print("-" * 78)
    for name, action_id, desc, holding, risk in ARMS:
        print(f"{name:<16}{action_id:<6}{desc:<36}{'是' if holding else '否':<8}{risk}")


def check_fsm(loco):
    """手臂动作只认 500/501/801；先查一次，能把 7404 提前讲清楚。"""
    code, fsm_id = loco.GetFsmId()
    if code != 0:
        print(f"[警告] GetFsmId 失败 code={code}，先跑 00_probe.py 查链路。")
        return
    print(f"当前 FSM = {fsm_id}")
    if fsm_id not in SUPPORTED_FSM:
        print("  注意：手臂动作只在 FSM 500 / 501 / 801 下可用。")
        print("  如果执行返回 7404，先跑: python3 02_loco.py --action start")


def main():
    parser = argparse.ArgumentParser(description="调用 G1 的手臂预置动作")
    parser.add_argument("--action", help="动作名，见 --list")
    parser.add_argument("--id", type=int, help="直接给 action_id，例如 27")
    parser.add_argument("--list", action="store_true", help="列出所有动作")
    parser.add_argument("--demo", action="store_true", help="按顺序做一小段")
    parser.add_argument("--release", action="store_true", help="动作后补 99 释放（默认就是这个行为）")
    parser.add_argument("--hold", action="store_true", help="保持型动作不自动释放")
    parser.add_argument("--iface", help="网卡名，如 eth0；不填则用 CYCLONEDDS_URI")
    parser.add_argument("--yes", action="store_true", help="跳过回车确认")
    args = parser.parse_args()

    if args.list:
        print_list()
        return

    if args.demo:
        sequence = ["high wave", "clap", "heart", "release arm"]
    elif args.id is not None:
        if args.id not in BY_ID:
            print(f"没有 action_id={args.id}。用 --list 看全部。")
            return
        sequence = [BY_ID[args.id][0]]
    elif args.action:
        if args.action not in BY_NAME:
            print(f"没有这个动作: {args.action}。用 --list 看全部。")
            return
        sequence = [args.action]
    else:
        print("要么 --list，要么 --action <名字>，要么 --id <编号>，要么 --demo。")
        print("  python3 03_arm_actions.py --list")
        print('  python3 03_arm_actions.py --action "high wave"')
        return

    if not args.yes:
        print("即将让 G1 做手臂动作。")
        print("确认：手臂活动范围内没人、没桌子，手握急停。")
        input("按回车继续，Ctrl+C 取消: ")

    if args.iface:
        ChannelFactoryInitialize(0, args.iface)
    else:
        ChannelFactoryInitialize(0)

    loco = LocoClient()
    loco.SetTimeout(5.0)
    loco.Init()

    arm = G1ArmActionClient()
    arm.SetTimeout(10.0)
    arm.Init()

    check_fsm(loco)

    # 默认释放；--hold 保持；--release 只是把默认行为写明白。
    release_after = args.release or not args.hold

    try:
        for name in sequence:
            _, action_id, desc, holding, _ = BY_NAME[name]
            print(f'\n[ExecuteAction({action_id})] "{name}" - {desc}')
            explain(arm.ExecuteAction(action_id))
            time.sleep(2.0)

            # 保持型动作默认补一条 release，避免手臂一直端着。
            if holding and release_after and name != "release arm":
                print("[ExecuteAction(99)] 自动释放手臂（--hold 可关闭）")
                explain(arm.ExecuteAction(action_map["release arm"]))
                time.sleep(1.0)
    finally:
        print("\n[收尾] release arm (99)")
        explain(arm.ExecuteAction(action_map["release arm"]))


if __name__ == "__main__":
    main()
