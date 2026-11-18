#!/usr/bin/env python3
"""02b G1 高层控制：给 LocoClient 下速度，让它往前走。

低层给关节力矩，中层给步态（固件里的 MPC/WBC 在跑），高层只干一件事：
    client.SetVelocity(vx, vy, wz, duration)
每 50 ms 说一句"向前 0.3 m/s、左移 0、转身 0"。本脚本就是这一层的全部内容。

三条要记住的：
  1. 三个数在**机体坐标系**：vx 前、vy 左、wz 逆时针；不是世界坐标系。
  2. G1 的 SetVelocity **带 duration**，是"我预授权你走这么多秒"。
     断流了它会把这一段走完 —— 和 Go2 完全相反（见 go2/02b_high_level_move.py）。
  3. SDK 只给速度，不给坐标。"去 (1, 0.5) 那个点"要自己闭环，见 --action goto。

反馈来源：rt/sportmodestate（unitree_go 的 SportModeState，不是 unitree_hg）。
    position  运控里程计的世界坐标，会漂
    velocity  机体坐标系线速度
    imu_state.rpy[2]  yaw

用法:
    python3 02b_high_level_move.py --action probe
    python3 02b_high_level_move.py --action twist --vx 0.2 --duration 2
    python3 02b_high_level_move.py --action dropout      # 走 3 秒，看它断流后还走不走
    python3 02b_high_level_move.py --action circle --vx 0.2 --wz 0.3 --duration 4
    python3 02b_high_level_move.py --action goto --x 1.0 --y 0.5
    python3 02b_high_level_move.py --action stop

安全:
    默认先按回车确认，--yes 跳过。
    不管怎么退出，finally 里一定 SetVelocity(0,0,0)。
    第一次上真机：vx≤0.2，duration≤2 s，手放在急停上。
"""
import argparse
import math
import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient
from unitree_sdk2py.idl.unitree_go.msg.dds_ import SportModeState_

# G1 和 Go2 的运控状态话题是同一个 DDS 名字，消息类型都是 unitree_go。
# （G1 的 LowState 才是 unitree_hg —— 这两个别混。）
STATE_TOPIC = "rt/sportmodestate"

# 速度上限，防手滑
VX_LIMIT = 0.6
VY_LIMIT = 0.4
WZ_LIMIT = 1.0

# 每一段速度预授权多少秒。发得勤就短，断流实验就故意给长。
SEG = 0.5

RPC_ERRORS = {
    3102: "请求没发出去（网卡 / DDS 配置）",
    3104: "等机器人回复超时（没在听，或当前状态不允许）",
    3203: "固件没实现这个接口（型号 / 版本不支持）",
    3204: "参数不对",
    7301: "LocoState 不可用：运控服务还没起来",
    7302: "FSM ID 非法：这个机型不支持该状态",
    7303: "Task ID 非法",
}


def explain(code):
    if code == 0:
        return "ok"
    return f"失败({code})：{RPC_ERRORS.get(code, '非 0，先确认机器人站立、没被 App/遥控器接管')}"


# ---------------------------------------------------------------- 状态缓存
class State:
    """后台订阅 rt/sportmodestate，主循环随时取最新一帧。"""

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
    """归一化到 [-pi, pi]。差一个 2pi，atan2 会让机器人原地转圈。"""
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


def action_twist(client, st, vx, vy, wz, duration, hz, seg):
    """最基础的一课：以 hz 重复发同一条速度，持续 duration 秒。"""
    vx, vy, wz = (clamp(vx, -VX_LIMIT, VX_LIMIT),
                  clamp(vy, -VY_LIMIT, VY_LIMIT),
                  clamp(wz, -WZ_LIMIT, WZ_LIMIT))
    period = 1.0 / hz
    print(f"[twist] vx={vx:+.2f} vy={vy:+.2f} wz={wz:+.2f} | {hz:.0f} Hz 重发，每段 {seg:.1f} s，共 {duration:.1f} s")

    t0 = time.time()
    next_print = t0
    while time.time() - t0 < duration:
        code = client.SetVelocity(vx, vy, wz, seg)
        if code != 0:
            print(f"  SetVelocity -> {explain(code)}")
            return

        now = time.time()
        if st.fresh() and now >= next_print:
            avx, avy, _ = st.msg.velocity
            print(f"  t={now - t0:4.1f}s 指令=({vx:+.2f},{vy:+.2f}) 实测机体=({avx:+.2f},{avy:+.2f})")
            next_print = now + 0.5
        time.sleep(period)


def action_dropout(client, st, vx, duration):
    """G1 的招牌行为：只发一条带 duration 的指令，然后闭嘴。

    duration = 我预授权你走这么多秒。所以断流之后它**不会**立刻停，
    会把这 3 秒老老实实走完。这是和 Go2 最大的设计差异。
    """
    vx = clamp(vx, -VX_LIMIT, VX_LIMIT)
    print(f"[dropout] 只发一条 SetVelocity(vx={vx:+.2f}, duration={duration:.1f})，然后 {duration:.1f} s 内一条都不发")
    code = client.SetVelocity(vx, 0.0, 0.0, duration)
    print(f"  发送 -> {explain(code)}")

    t0 = time.time()
    while time.time() - t0 < duration:
        if st.fresh():
            avx = st.msg.velocity[0]
            flag = "还在走" if abs(avx) > 0.05 else "已停下"
            print(f"  t={time.time() - t0:4.1f}s 实测 vx={avx:+.3f}  {flag}")
        time.sleep(0.5)

    print("  预授权时间用完，看它自己收住 —— 这就是 duration 的含义。")
    print("  对比：Go2 的 Move 没有 duration，断流几百毫秒固件就自己停。")


def action_circle(client, st, vx, wz, duration, hz, seg):
    print(f"[circle] vx={vx:+.2f} wz={wz:+.2f}，半径约 {vx / max(abs(wz), 1e-3):.2f} m")
    action_twist(client, st, vx, 0.0, wz, duration, hz, seg)


def action_goto(client, st, gx, gy, hz, timeout, seg, kp=0.8, kyaw=1.2):
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

        code = client.SetVelocity(vx, vy, wz, seg)
        if code != 0:
            print(f"  SetVelocity -> {explain(code)}")
            return
        time.sleep(1.0 / hz)


# ---------------------------------------------------------------- 入口
def main():
    p = argparse.ArgumentParser(description="G1 高层运动控制：速度指令与闭环到点")
    p.add_argument("--action", default="probe",
                   choices=["probe", "twist", "dropout", "circle", "goto", "stop"])
    p.add_argument("--vx", type=float, default=0.2, help="前进速度 m/s")
    p.add_argument("--vy", type=float, default=0.0, help="左移速度 m/s")
    p.add_argument("--wz", type=float, default=0.0, help="转向 rad/s")
    p.add_argument("--duration", type=float, default=2.0, help="持续 / 预授权时间 s")
    p.add_argument("--hz", type=float, default=20.0, help="重发频率 Hz")
    p.add_argument("--seg", type=float, default=SEG, help="每段 SetVelocity 的 duration s")
    p.add_argument("--x", type=float, default=1.0, help="goto 目标 x（世界系）")
    p.add_argument("--y", type=float, default=0.0, help="goto 目标 y（世界系）")
    p.add_argument("--timeout", type=float, default=20.0, help="goto 超时 s")
    p.add_argument("--iface", help="网卡名，如 eth0；不填则用 CYCLONEDDS_URI")
    p.add_argument("--yes", action="store_true", help="跳过回车确认")
    args = p.parse_args()

    if args.action != "probe" and not args.yes:
        print(f"即将让 G1 执行 {args.action}。")
        print("确认：场地清空、周围 2 m 无人、手握急停。")
        input("按回车继续，Ctrl+C 取消: ")

    if args.iface:
        ChannelFactoryInitialize(0, args.iface)
    else:
        ChannelFactoryInitialize(0)

    st = State()
    ok = st.start()
    if not ok:
        print(f"[警告] 3 秒内没收到 {STATE_TOPIC}。没有反馈也能发指令，但那叫盲开。")
    if args.action == "probe":
        action_probe(st)
        st.close()
        return

    client = LocoClient()
    client.SetTimeout(10.0)
    client.Init()

    # 走高层控制前必须进主运控 FSM 500，否则 7105 会回 7301 / 7302。
    if args.action != "stop":
        print(f"  SetFsmId(500) -> {explain(client.SetFsmId(500))}")
        time.sleep(1.0)

    try:
        if args.action == "twist":
            action_twist(client, st, args.vx, args.vy, args.wz, args.duration, args.hz, args.seg)
        elif args.action == "dropout":
            action_dropout(client, st, args.vx, args.duration)
        elif args.action == "circle":
            action_circle(client, st, args.vx, args.wz or 0.3, args.duration, args.hz, args.seg)
        elif args.action == "goto":
            action_goto(client, st, args.x, args.y, args.hz, args.timeout, args.seg)
        elif args.action == "stop":
            pass
    finally:
        # 正常结束、超时、Ctrl+C —— 一律清零。这条不能省。
        print("[收尾] SetVelocity(0,0,0)")
        print(f"  -> {explain(client.SetVelocity(0.0, 0.0, 0.0, 1.0))}")
        st.close()


if __name__ == "__main__":
    main()
