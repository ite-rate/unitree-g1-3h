#!/usr/bin/env python3
# Go2 附加章节。补 3 行路径引导，这样从 go2/ 目录直接运行时，
# 也能 import 到仓库根目录的 unitree_sdk2py（和 go2/02_actions.py 一样）。
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
"""go2/02b 高层控制：给 SportClient 下速度，让狗走起来。

低层给关节力矩，中层给步态（固件里的 MPC 在跑），高层只干一件事：
    client.Move(vx, vy, vyaw)
每 50 ms 说一句"向前 0.3 m/s、左移 0、转身 0"。本脚本就是这一层的全部内容。

狗和人（G1）在高层的三个关键差异：
  1. Move() 是 _CallNoReply —— 发出去就 return 0，**没有回执**，你根本不知道固件收没收到。
  2. Move() **没有 duration** —— 一次性调用，它走一小段就停。想连续走，必须自己按频率重复发。
  3. 断流保护在固件里：上层不发指令，几百毫秒后它自己停下（不是 bug，是安全设计）。
     所以 Go2 这一节的核心词是「持续的数据流」，不是「一次函数调用」。
     G1 反过来，SetVelocity 带 duration，断流后会把这 3 秒走完。见根目录 02b。

反馈来源：rt/sportmodestate（unitree_go 的 SportModeState）。
    position  运控里程计的世界坐标，会漂
    velocity  机体坐标系线速度
    imu_state.rpy[2]  yaw

用法:
    python3 go2/02b_high_level_move.py --action probe
    python3 go2/02b_high_level_move.py --action twist --vx 0.3 --duration 2
    python3 go2/02b_high_level_move.py --action dropout       # 断流 1.5 s，看它自己停
    python3 go2/02b_high_level_move.py --action circle --vx 0.2 --wz 0.3 --duration 4
    python3 go2/02b_high_level_move.py --action goto --x 1.0 --y 0.5
    python3 go2/02b_high_level_move.py --action stop

安全:
    默认先按回车确认，--yes 跳过。
    不管怎么退出，finally 里一定 StopMove()。
    第一次上真机：vx≤0.3，duration≤2 s，手放在急停上。
"""
import argparse
import math
import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.go2.sport.sport_client import SportClient
from unitree_sdk2py.idl.unitree_go.msg.dds_ import SportModeState_

# 与 G1 同一条 DDS 话题名、同一个消息类型；ROS 2 里 remap 成 /sportmodestate。
STATE_TOPIC = "rt/sportmodestate"

VX_LIMIT = 0.8      # 狗比人快，上限给宽一点
VY_LIMIT = 0.4
WZ_LIMIT = 1.2

RPC_ERRORS = {
    3102: "请求没发出去（网卡 / DDS 配置）",
    3104: "等机器人回复超时（没在听，或当前状态不允许）",
    3203: "固件没实现这个接口（型号 / 版本不支持）",
    3204: "参数不对",
}


def explain(code):
    if code == 0:
        return "ok"
    return f"失败({code})：{RPC_ERRORS.get(code, '非 0，先 BalanceStand 站稳、别被 App 接管')}"


# ---------------------------------------------------------------- 状态缓存
class State:
    def __init__(self):
        self.msg = None
        self.t = 0.0
        self.sub = None

    def start(self):
        self.sub = ChannelSubscriber(STATE_TOPIC, SportModeState_)
        self.sub.Init(self._cb, 10)
        t0 = time.time()
        while self.msg is None and time.time() - t0 < 3.0:
            time.sleep(0.05)
        return self.msg is not None

    def _cb(self, msg):
        self.msg, self.t = msg, time.time()

    def fresh(self, max_age=0.5):
        return self.msg is not None and time.time() - self.t < max_age

    def pose(self):
        m = self.msg
        return m.position[0], m.position[1], m.imu_state.rpy[2]

    def close(self):
        if self.sub is not None:
            try:
                self.sub.Close()
            except Exception:
                pass


# ---------------------------------------------------------------- 指令
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def wrap(a):
    while a > math.pi:
        a -= 2 * math.pi
    while a < -math.pi:
        a += 2 * math.pi
    return a


def show_state(st, prefix="  "):
    x, y, yaw = st.pose()
    vx, vy, _ = st.msg.velocity
    print(f"{prefix}pos=({x:+.2f}, {y:+.2f}) yaw={math.degrees(yaw):+6.1f}° "
          f"| v_body=({vx:+.2f}, {vy:+.2f}) m/s | gait={st.msg.gait_type} mode={st.msg.mode}")


def action_probe(st):
    if st.msg is None:
        print(f"3 秒内没收到 {STATE_TOPIC}。查网卡 / DDS / 机器人是否被 App 或遥控器接管。")
        return
    print(f"{STATE_TOPIC} 采样中：")
    for _ in range(10):
        if st.msg is not None:
            show_state(st)
        time.sleep(0.2)


def action_twist(client, st, vx, vy, wz, duration, hz):
    """这一节的核心：hz 频率重复发同一条速度。

    Move() 没有 duration，所以"走 2 秒"完全由这个循环实现 ——
    循环停了，狗就停。学生第一次看到"控制频率"这四个字有实体。
    """
    vx, vy, wz = (clamp(vx, -VX_LIMIT, VX_LIMIT),
                  clamp(vy, -VY_LIMIT, VY_LIMIT),
                  clamp(wz, -WZ_LIMIT, WZ_LIMIT))
    period = 1.0 / hz
    print(f"[twist] vx={vx:+.2f} vy={vy:+.2f} wz={wz:+.2f} | {hz:.0f} Hz 重发，共 {duration:.1f} s")

    t0 = time.time()
    next_print = t0
    n = 0
    while time.time() - t0 < duration:
        client.Move(vx, vy, wz)     # ← 无回执，返回值永远是 0，别拿它判断成败
        n += 1

        now = time.time()
        if st.fresh() and now >= next_print:
            avx, avy, _ = st.msg.velocity
            print(f"  t={now - t0:4.1f}s 已发 {n} 条 指令=({vx:+.2f},{vy:+.2f}) 实测机体=({avx:+.2f},{avy:+.2f})")
            next_print = now + 0.5
        time.sleep(period)
    print(f"  共发出 {n} 条，约 {n / max(duration, 1e-6):.0f} Hz")


def action_dropout(client, st, vx, duration, gap):
    """狗这一节最值钱的实验：走一会儿，然后故意闭嘴，看它停不停。

    Go2 的 Move 没有 duration，所以你在 gap 秒内一条不发 → 固件超时保护接管 → 自己停。
    这就是"高层控制是数据流，不是函数调用"的证据。
    （具体超时阈值随固件版本略有差别，现场以实测为准。）
    """
    vx = clamp(vx, -VX_LIMIT, VX_LIMIT)
    hz = 20.0
    print(f"[dropout] 先以 {hz:.0f} Hz 发 vx={vx:+.2f} 走 {duration:.1f} s，然后 {gap:.1f} s 一条都不发")

    t0 = time.time()
    while time.time() - t0 < duration:
        client.Move(vx, 0.0, 0.0)
        time.sleep(1.0 / hz)

    print(f"  >>> 停止发指令（{gap:.1f} s 内一条都不发）")
    t1 = time.time()
    while time.time() - t1 < gap:
        if st.fresh():
            avx = st.msg.velocity[0]
            flag = "还在走" if abs(avx) > 0.05 else "已经自己停了"
            print(f"  t={time.time() - t1:4.1f}s 实测 vx={avx:+.3f}  {flag}")
        time.sleep(0.25)

    print("  对比：G1 的 SetVelocity 带 duration，同样断流它会把这 3 秒走完。")


def action_circle(client, st, vx, wz, duration, hz):
    print(f"[circle] vx={vx:+.2f} wz={wz:+.2f}，半径约 {vx / max(abs(wz), 1e-3):.2f} m")
    action_twist(client, st, vx, 0.0, wz, duration, hz)


def action_goto(client, st, gx, gy, hz, timeout, kp=0.8, kyaw=1.2):
    """自己写一个 MoveTo：SDK 没有位置接口，位置闭环在上层。

    控制律四行：
        世界系误差 -> 机体系误差（★ 这行写错就绕圈）
        vx = kp * ex_b
        wz = kyaw * bearing
    保护：方向偏差大先原地转 / 到点死区 0.1 m / 超时或断流立刻停。
    """
    if not st.fresh():
        print("[goto] 没有 rt/sportmodestate 反馈，位置控制没法做。先 --action probe。")
        return

    print(f"[goto] 目标 ({gx:+.2f}, {gy:+.2f})")
    t0 = time.time()
    while True:
        if time.time() - t0 > timeout:
            print("  超时，放弃。")
            return
        if not st.fresh():
            print("  反馈断了，停车。")
            return

        x, y, yaw = st.pose()
        ex, ey = gx - x, gy - y
        dist = math.hypot(ex, ey)
        print(f"  pos=({x:+.2f},{y:+.2f}) 误差=({ex:+.2f},{ey:+.2f}) 距离={dist:.2f} m")
        if dist < 0.10:
            print("  到点了。")
            return

        c, s = math.cos(yaw), math.sin(yaw)
        ex_b = c * ex + s * ey      # ★ 世界系 -> 机体系，少了这两行必画弧
        ey_b = -s * ex + c * ey
        bearing = math.atan2(ey_b, ex_b)

        if abs(bearing) > 0.6:
            vx, vy, wz = 0.0, 0.0, clamp(kyaw * wrap(bearing), -WZ_LIMIT, WZ_LIMIT)
        else:
            vx = clamp(kp * ex_b, -VX_LIMIT, VX_LIMIT)
            vy = clamp(0.4 * ey_b, -VY_LIMIT, VY_LIMIT)
            wz = clamp(kyaw * wrap(bearing), -WZ_LIMIT, WZ_LIMIT)

        client.Move(vx, vy, wz)
        time.sleep(1.0 / hz)


# ---------------------------------------------------------------- 入口
def main():
    p = argparse.ArgumentParser(description="Go2 高层运动控制：速度指令与闭环到点")
    p.add_argument("--action", default="probe",
                   choices=["probe", "twist", "dropout", "circle", "goto", "stop"])
    p.add_argument("--vx", type=float, default=0.3, help="前进速度 m/s")
    p.add_argument("--vy", type=float, default=0.0, help="左移速度 m/s")
    p.add_argument("--wz", type=float, default=0.0, help="转向 rad/s")
    p.add_argument("--duration", type=float, default=2.0, help="持续时间 s")
    p.add_argument("--gap", type=float, default=1.5, help="dropout 断流时长 s")
    p.add_argument("--hz", type=float, default=20.0, help="重发频率 Hz")
    p.add_argument("--x", type=float, default=1.0, help="goto 目标 x（世界系）")
    p.add_argument("--y", type=float, default=0.0, help="goto 目标 y（世界系）")
    p.add_argument("--timeout", type=float, default=20.0, help="goto 超时 s")
    p.add_argument("--iface", help="网卡名，如 eth0；不填则用 CYCLONEDDS_URI")
    p.add_argument("--yes", action="store_true", help="跳过回车确认")
    args = p.parse_args()

    if args.action != "probe" and not args.yes:
        print(f"即将让 Go2 执行 {args.action}。")
        print("确认：场地清空、周围 2 m 无人、手握急停。")
        input("按回车继续，Ctrl+C 取消: ")

    if args.iface:
        ChannelFactoryInitialize(0, args.iface)
    else:
        ChannelFactoryInitialize(0)

    st = State()
    if not st.start():
        print(f"[警告] 3 秒内没收到 {STATE_TOPIC}。没有反馈也能发指令，但那叫盲开。")
    if args.action == "probe":
        action_probe(st)
        st.close()
        return

    client = SportClient()
    client.SetTimeout(10.0)
    client.Init()

    # 走路之前先站稳。Go2 上是 BalanceStand（1002），不是 G1 的 FSM 500。
    if args.action != "stop":
        print(f"  BalanceStand() -> {explain(client.BalanceStand())}")
        time.sleep(1.0)

    try:
        if args.action == "twist":
            action_twist(client, st, args.vx, args.vy, args.wz, args.duration, args.hz)
        elif args.action == "dropout":
            action_dropout(client, st, args.vx, args.duration, args.gap)
        elif args.action == "circle":
            action_circle(client, st, args.vx, args.wz or 0.3, args.duration, args.hz)
        elif args.action == "goto":
            action_goto(client, st, args.x, args.y, args.hz, args.timeout)
        elif args.action == "stop":
            pass
    finally:
        # 正常结束、超时、Ctrl+C —— 一律停车。这条不能省。
        print("[收尾] StopMove()")
        print(f"  -> {explain(client.StopMove())}")
        st.close()


if __name__ == "__main__":
    main()
