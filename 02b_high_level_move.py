#!/usr/bin/env python3
"""02b G1 高层控制：给 LocoClient 下速度，让它真的走起来。

高层控制只干一件事，每 50 ms 说一句：
    client.SetVelocity(vx, vy, wz, duration)
三个数都在机体坐标系：vx 前、vy 左、wz 逆时针。

G1 的 duration 是"预授权时长"：断流了它会把这一段走完
（和 Go2 完全相反，用 --action dropout 现场对比）。
SDK 只给速度不给坐标，"去 (1.0, 0.5) 那个点"要自己闭环，--action goto。

用法:
    python3 02b_high_level_move.py --action probe
    python3 02b_high_level_move.py --action walk --vx 0.2 --duration 2
    python3 02b_high_level_move.py --action dropout --vx 0.2 --duration 3
    python3 02b_high_level_move.py --action goto --x 1.0 --y 0.5
    python3 02b_high_level_move.py --action stop
"""
import argparse
import math
import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient
from unitree_sdk2py.idl.unitree_go.msg.dds_ import SportModeState_

# 反馈来源：G1 和 Go2 用同一条话题、同一个 unitree_go 类型
STATE_TOPIC = "rt/sportmodestate"
VX_LIMIT, VY_LIMIT, WZ_LIMIT = 0.6, 0.4, 1.0   # 速度上限，防手滑

box = {"msg": None, "t": 0.0}   # 最新一帧反馈 + 收到它的时刻


def on_state(msg: SportModeState_):
    box["msg"], box["t"] = msg, time.time()


def show_state():
    m = box["msg"]
    x, y = m.position[0], m.position[1]
    vx, vy = m.velocity[0], m.velocity[1]
    yaw = math.degrees(m.imu_state.rpy[2])
    print(f"  pos=({x:+.2f}, {y:+.2f}) yaw={yaw:+6.1f}°  实测 v=({vx:+.2f}, {vy:+.2f}) m/s")


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def main():
    parser = argparse.ArgumentParser(description="G1 高层运动控制")
    parser.add_argument("--action", default="probe",
                        choices=["probe", "walk", "dropout", "circle", "goto", "stop"])
    parser.add_argument("--vx", type=float, default=0.2, help="前进速度 m/s")
    parser.add_argument("--vy", type=float, default=0.0, help="左移速度 m/s")
    parser.add_argument("--wz", type=float, default=0.0, help="转向 rad/s")
    parser.add_argument("--duration", type=float, default=2.0, help="持续 / 预授权秒数")
    parser.add_argument("--x", type=float, default=1.0, help="goto 目标 x（世界系）")
    parser.add_argument("--y", type=float, default=0.0, help="goto 目标 y（世界系）")
    parser.add_argument("--yes", action="store_true", help="跳过回车确认")
    args = parser.parse_args()

    if args.action not in ("probe", "stop") and not args.yes:
        print(f"即将让 G1 执行 {args.action}。确认：场地清空、周围 2 m 无人、手握急停。")
        input("按回车继续，Ctrl+C 取消: ")

    ChannelFactoryInitialize(0)

    sub = ChannelSubscriber(STATE_TOPIC, SportModeState_)
    sub.Init(on_state, 10)
    time.sleep(1.0)
    if box["msg"] is None:
        print(f"[警告] 没收到 {STATE_TOPIC}。能发指令但那是盲开，先查链路。")
        if args.action == "probe":
            sub.Close()
            return

    if args.action == "probe":
        for _ in range(10):
            if box["msg"] is not None:
                show_state()
            time.sleep(0.2)
        sub.Close()
        return

    client = LocoClient()
    client.SetTimeout(10.0)
    client.Init()

    # 走之前必须进主运控 FSM 500，否则 SetVelocity 回 7301 / 7302
    if args.action != "stop":
        print("SetFsmId(500) ->", client.SetFsmId(500))
        time.sleep(1.0)

    try:
        if args.action in ("walk", "circle"):
            # 最基础的一课：20 Hz 重发同一条速度
            vx, vy = args.vx, args.vy
            wz = (args.wz or 0.3) if args.action == "circle" else args.wz
            print(f"SetVelocity({vx:+.2f}, {vy:+.2f}, {wz:+.2f})，20 Hz 重发 {args.duration:.0f} 秒")
            t0 = time.monotonic()
            while time.monotonic() - t0 < args.duration:
                code = client.SetVelocity(clamp(vx, -VX_LIMIT, VX_LIMIT),
                                          clamp(vy, -VY_LIMIT, VY_LIMIT),
                                          clamp(wz, -WZ_LIMIT, WZ_LIMIT), 0.5)
                if code != 0:
                    print(f"  code = {code}，停下。")
                    break
                time.sleep(0.05)

        elif args.action == "dropout":
            # 只发一条带 duration 的指令，然后闭嘴 —— 看它把这段走完
            print(f"只发一条 SetVelocity({args.vx:+.2f}, 0, 0, duration={args.duration:.0f})，然后一条都不发")
            print("SetVelocity ->", client.SetVelocity(args.vx, 0.0, 0.0, args.duration))
            t0 = time.monotonic()
            while time.monotonic() - t0 < args.duration:
                if box["msg"] is not None:
                    v = box["msg"].velocity[0]
                    print(f"  t={time.monotonic() - t0:4.1f}s 实测 vx={v:+.3f} "
                          f"{'还在走' if abs(v) > 0.05 else '已停下'}")
                time.sleep(0.5)
            print("  预授权用完它自己收住 —— 这就是 duration 的含义。")
            print("  对比 Go2：Move 没有 duration，断流几百毫秒固件就自己停。")

        elif args.action == "goto":
            # SDK 没有位置接口，位置闭环在上层。控制律就四行：
            #   世界系误差 -> 机体系误差（★ 这行旋转少了机器人就绕圈）
            if box["msg"] is None:
                print("没有反馈做不了位置闭环。")
            else:
                gx, gy = args.x, args.y
                t0 = time.monotonic()
                while True:
                    if time.monotonic() - t0 > 20.0:
                        print("  超时，放弃。"); break
                    if time.time() - box["t"] > 0.5:
                        print("  反馈断了，停车。"); break
                    m = box["msg"]
                    x, y, yaw = m.position[0], m.position[1], m.imu_state.rpy[2]
                    ex, ey = gx - x, gy - y
                    dist = math.hypot(ex, ey)
                    print(f"  pos=({x:+.2f},{y:+.2f}) 距离={dist:.2f} m")
                    if dist < 0.10:
                        print("  到点了。"); break
                    c, s = math.cos(yaw), math.sin(yaw)
                    ex_b, ey_b = c * ex + s * ey, -s * ex + c * ey   # ★ 世界系 -> 机体系
                    bearing = math.atan2(ey_b, ex_b)
                    vx = 0.0 if abs(bearing) > 0.6 else clamp(0.8 * ex_b, -VX_LIMIT, VX_LIMIT)
                    wz = clamp(1.2 * bearing, -WZ_LIMIT, WZ_LIMIT)
                    code = client.SetVelocity(vx, 0.0, wz, 0.5)
                    if code != 0:
                        print(f"  code = {code}，停下。"); break
                    time.sleep(0.05)

    finally:
        # 正常、超时、Ctrl+C —— 一律清零。这条不能省。
        print("[收尾] SetVelocity(0,0,0) ->", client.SetVelocity(0.0, 0.0, 0.0, 1.0))
        sub.Close()


if __name__ == "__main__":
    main()
