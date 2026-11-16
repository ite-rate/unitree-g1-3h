#!/usr/bin/env python3
# 附加章节：Go2 版本。保留原脚本，逻辑未改，只补了下面 3 行路径引导，
# 这样从 go2/ 目录直接运行时，也能 import 到仓库根目录的 unitree_sdk2py。
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
"""07 综合演示：一条命令把今天的东西串起来。

流程（真机演示顺序）：
    1. 读 /lowstate：电量、姿态
    2. 头部 LED 调到 10，音量调到 8
    3. 站稳 -> 打招呼 -> 伸懒腰 -> 跳舞 1 -> 停
    4. 前置摄像头抓一张照片
    5. 激光雷达看 5 秒，打印最近障碍物
    6. 恢复灯光和音量

用法:
    python3 07_demo_show.py
    python3 07_demo_show.py --yes
    python3 07_demo_show.py --iface eth0 --seconds 8

安全：默认会停下来等你确认。请清场、留出 2 m、手握急停。
"""
import argparse
import math
import time
from pathlib import Path

import numpy as np

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.go2.sport.sport_client import SportClient
from unitree_sdk2py.go2.video.video_client import VideoClient
from unitree_sdk2py.go2.vui.vui_client import VuiClient
from unitree_sdk2py.idl.sensor_msgs.msg.dds_ import PointCloud2_
from unitree_sdk2py.idl.unitree_go.msg.dds_ import LowState_

OUT = Path(__file__).resolve().parent / "out"


def stage(text):
    print(f"\n===== {text} =====")


def read_status(seconds=2.0):
    box = {"msg": None}
    sub = ChannelSubscriber("rt/lowstate", LowState_)
    sub.Init(lambda m: box.__setitem__("msg", m), 10)
    time.sleep(seconds)
    sub.Close()

    msg = box["msg"]
    if msg is None:
        print("没有收到 /lowstate，先跑 00_probe.py 排障。")
        return False
    print(f"电量 {msg.bms_state.soc}% | 电压 {msg.power_v:.2f} V")
    print(f"yaw {msg.imu_state.rpy[2]:+.2f} rad | 姿态 roll {msg.imu_state.rpy[0]:+.2f}")
    return True


def lidar_brief(seconds):
    box = {"frames": 0, "last": None, "t": 0.0}

    def on_cloud(msg: PointCloud2_):
        box["frames"] += 1
        now = time.monotonic()
        if now - box["t"] < 0.5:
            return
        box["t"] = now

        step = msg.point_step
        total = msg.width * msg.height
        raw = np.frombuffer(bytes(msg.data), dtype=np.uint8)
        if step <= 0 or total <= 0 or raw.size < total * step:
            return
        offsets = {f.name: f.offset for f in msg.fields}
        if not {"x", "y", "z"} <= offsets.keys():
            return
        rows = raw[: total * step].reshape(total, step)
        xyz = np.empty((total, 3), dtype=np.float32)
        for i, name in enumerate(("x", "y", "z")):
            off = offsets[name]
            xyz[:, i] = rows[:, off:off + 4].copy().view(np.float32).ravel()
        xyz = xyz[np.isfinite(xyz).all(axis=1)]
        r = np.hypot(xyz[:, 0], xyz[:, 1])
        keep = r > 0.05
        xyz, r = xyz[keep], r[keep]
        if len(xyz) == 0:
            return
        i = int(np.argmin(r))
        front = xyz[(xyz[:, 0] > 0.1) & (np.abs(xyz[:, 1]) < 1.0)]
        front_min = float(np.hypot(front[:, 0], front[:, 1]).min()) if len(front) else float("nan")
        angle = math.degrees(math.atan2(xyz[i, 1], xyz[i, 0]))
        box["last"] = (len(xyz), float(r[i]), angle, front_min)

    sub = ChannelSubscriber("rt/utlidar/cloud", PointCloud2_)
    sub.Init(on_cloud, 1)
    t0 = time.time()
    while time.time() - t0 < seconds:
        time.sleep(1.0)
        if box["last"] is None:
            print("  等待点云 ...")
            continue
        n, nearest, angle, front_min = box["last"]
        print(f"  {n} 点 | 最近 {nearest:.2f} m @ {angle:+.0f}° | 前方 {front_min:.2f} m")
    sub.Close()
    if box["frames"] == 0:
        print("  没收到点云：检查 04_lidar.py --switch on，或用 00_probe.py 查链路。")


def main():
    parser = argparse.ArgumentParser(description="Go2 三小时课程综合演示")
    parser.add_argument("--iface", help="网卡名，如 eth0；不填则用 CYCLONEDDS_URI")
    parser.add_argument("--yes", action="store_true", help="跳过回车确认")
    parser.add_argument("--seconds", type=float, default=5.0, help="雷达观察时长")
    args = parser.parse_args()

    if not args.yes:
        print("即将让机器人做动作：站稳、打招呼、伸懒腰、跳舞。")
        print("确认：场地清空、周围 2 m 无人、手握急停。")
        input("按回车开始，Ctrl+C 取消: ")

    if args.iface:
        ChannelFactoryInitialize(0, args.iface)
    else:
        ChannelFactoryInitialize(0)

    vui = VuiClient()
    vui.SetTimeout(3.0)
    vui.Init()

    sport = SportClient()
    sport.SetTimeout(10.0)
    sport.Init()

    video = VideoClient()
    video.SetTimeout(3.0)
    video.Init()

    try:
        stage("1. 读状态")
        if not read_status():
            return

        stage("2. 灯与音量")
        print("亮度 -> 10，音量 -> 8")
        print("SetBrightness:", vui.SetBrightness(10))
        print("SetVolume:    ", vui.SetVolume(8))

        stage("3. 预设动作")
        for label, call, wait in (
            ("BalanceStand", sport.BalanceStand, 1.0),
            ("Hello", sport.Hello, 3.0),
            ("Stretch", sport.Stretch, 3.0),
            ("Dance1", sport.Dance1, 6.0),
        ):
            code = call()
            print(f"{label:<14} code={code}")
            time.sleep(wait)

        stage("4. 前置摄像头")
        code, data = video.GetImageSample()
        if code == 0:
            OUT.mkdir(exist_ok=True)
            path = OUT / "demo_shot.jpg"
            path.write_bytes(bytes(data))
            print(f"已保存 {path}（{len(data) / 1024:.1f} KB）")
        else:
            print(f"取图失败 code={code}")

        stage("5. 激光雷达")
        lidar_brief(args.seconds)

    finally:
        stage("6. 收尾")
        print("StopMove:", sport.StopMove())
        print("恢复亮度 5、音量 5")
        vui.SetBrightness(5)
        vui.SetVolume(5)
        print("\n演示结束。")


if __name__ == "__main__":
    main()
