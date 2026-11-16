#!/usr/bin/env python3
"""05 G1 关节监视：把 /lowstate 里的 29 个关节读成人话。

一帧 LowState 里最重要的是 motor_state[35]：
    q        关节角（rad）
    dq       关节角速度（rad/s）
    tau_est  估计力矩（N·m）
    temperature[2]  两路温度（C）
    vol      母线电压（V）

G1 的关节顺序（29 DOF 机型）：
    0–11    两条腿
    12–14   腰（yaw / roll / pitch）
    15–21   左臂（肩 3 + 肘 + 腕 3）
    22–28   右臂（同上）

▶ 23 DOF 机型 / 腰部锁死的机型：13、14 无效；20、21、27、28 无效。
  这些槽位仍然在消息里，只是值没有意义，所以名字后面标了 *。

用法:
    python3 05_joint_monitor.py                    # 看 10 秒，每 1 秒刷新
    python3 05_joint_monitor.py --seconds 30
    python3 05_joint_monitor.py --joint 3          # 只看左膝
    python3 05_joint_monitor.py --joint L_knee
    python3 05_joint_monitor.py --csv out/joints.csv --seconds 60
    python3 05_joint_monitor.py --seconds 0        # 一直看，Ctrl+C 结束
"""
import argparse
import time
from pathlib import Path

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_

G1_MOTOR_COUNT = 29

# index / 短名 / 中文名 / 23DOF 是否有效
JOINTS = [
    (0,  "L_hip_pitch",     "左髋俯仰", True),
    (1,  "L_hip_roll",      "左髋横滚", True),
    (2,  "L_hip_yaw",       "左髋偏航", True),
    (3,  "L_knee",          "左膝",     True),
    (4,  "L_ankle_pitch",   "左踝俯仰", True),
    (5,  "L_ankle_roll",    "左踝横滚", True),
    (6,  "R_hip_pitch",     "右髋俯仰", True),
    (7,  "R_hip_roll",      "右髋横滚", True),
    (8,  "R_hip_yaw",       "右髋偏航", True),
    (9,  "R_knee",          "右膝",     True),
    (10, "R_ankle_pitch",   "右踝俯仰", True),
    (11, "R_ankle_roll",    "右踝横滚", True),
    (12, "waist_yaw",       "腰偏航",   True),
    (13, "waist_roll",      "腰横滚",   False),
    (14, "waist_pitch",     "腰俯仰",   False),
    (15, "L_shoulder_pitch", "左肩俯仰", True),
    (16, "L_shoulder_roll",  "左肩横滚", True),
    (17, "L_shoulder_yaw",   "左肩偏航", True),
    (18, "L_elbow",          "左肘",     True),
    (19, "L_wrist_roll",     "左腕横滚", True),
    (20, "L_wrist_pitch",    "左腕俯仰", False),
    (21, "L_wrist_yaw",      "左腕偏航", False),
    (22, "R_shoulder_pitch", "右肩俯仰", True),
    (23, "R_shoulder_roll",  "右肩横滚", True),
    (24, "R_shoulder_yaw",   "右肩偏航", True),
    (25, "R_elbow",          "右肘",     True),
    (26, "R_wrist_roll",     "右腕横滚", True),
    (27, "R_wrist_pitch",    "右腕俯仰", False),
    (28, "R_wrist_yaw",      "右腕偏航", False),
]
NAME_TO_INDEX = {name.lower(): idx for idx, name, _, _ in JOINTS}
NAME_BY_INDEX = {idx: name for idx, name, _, _ in JOINTS}


def resolve_joint(text: str):
    """--joint 既接受编号，也接受短名（大小写不敏感）。"""
    text = text.strip()
    if text.isdigit():
        idx = int(text)
        return idx if idx in NAME_BY_INDEX else None
    return NAME_TO_INDEX.get(text.lower().replace("-", "_"))


def print_sample(msg, selected, csv_file):
    now = time.time()
    for i in selected:
        m = msg.motor_state[i]
        name = NAME_BY_INDEX[i]
        temp = m.temperature[0]
        line = f"{i:>2} {name:<16} q={m.q:+7.3f} dq={m.dq:+7.3f} tau={m.tau_est:+6.2f} T={temp:>3d}C"
        print("  " + line)
        if csv_file:
            csv_file.write(f"{now:.3f},{i},{name},{m.q:.5f},{m.dq:.5f},{m.tau_est:.5f},{temp}\n")


def main():
    parser = argparse.ArgumentParser(description="监视 G1 的 29 个关节")
    parser.add_argument("--seconds", type=float, default=10.0, help="看多久；0 表示一直看")
    parser.add_argument("--joint", help="只看一个关节：编号 0–28 或名字，如 L_knee")
    parser.add_argument("--csv", help="把样本追加写入 CSV，如 out/joints.csv")
    parser.add_argument("--iface", help="网卡名，如 eth0；不填则用 CYCLONEDDS_URI")
    args = parser.parse_args()

    if args.joint is not None:
        idx = resolve_joint(args.joint)
        if idx is None:
            print(f"没有这个关节: {args.joint}")
            print("可用名字:", ", ".join(name for _, name, _, _ in JOINTS))
            return
        selected = [idx]
    else:
        selected = list(range(G1_MOTOR_COUNT))

    if args.iface:
        ChannelFactoryInitialize(0, args.iface)
    else:
        ChannelFactoryInitialize(0)

    box = {"count": 0, "last": None}

    def on_lowstate(msg: LowState_):
        box["count"] += 1
        box["last"] = msg

    sub = ChannelSubscriber("rt/lowstate", LowState_)
    sub.Init(on_lowstate, 10)
    print(f"订阅 rt/lowstate，{len(selected)} 个关节，每 1 s 刷新（Ctrl+C 结束）...")

    csv_file = None
    try:
        if args.csv:
            path = Path(args.csv)
            path.parent.mkdir(parents=True, exist_ok=True)
            new = not path.exists()
            csv_file = path.open("a", encoding="utf-8")
            if new:
                csv_file.write("t,index,name,q,dq,tau_est,temp\n")
            print(f"CSV -> {path}")

        t0 = time.monotonic()
        count_last = 0
        while True:
            time.sleep(1.0)
            elapsed = time.monotonic() - t0
            if args.seconds > 0 and elapsed >= args.seconds:
                break

            msg = box["last"]
            if msg is None:
                print("  还没收到 /lowstate，先跑 00_probe.py 查链路。")
                continue

            rate = box["count"] - count_last
            count_last = box["count"]
            print(f"\n[t={elapsed:5.1f}s] 本秒 {rate} 帧 | mode_machine={msg.mode_machine} "
                  f"| roll/pitch/yaw={msg.imu_state.rpy[0]:+.2f}/{msg.imu_state.rpy[1]:+.2f}/{msg.imu_state.rpy[2]:+.2f}")
            print_sample(msg, selected, csv_file)
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        sub.Close()
        if csv_file:
            csv_file.close()

    print("\n提示：q 是关节角，不是末端位置；想看末端位姿要自己做正运动学，或去配套 lab 课程。")


if __name__ == "__main__":
    main()
