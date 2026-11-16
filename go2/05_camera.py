#!/usr/bin/env python3
# 附加章节：Go2 版本。保留原脚本，逻辑未改，只补了下面 3 行路径引导，
# 这样从 go2/ 目录直接运行时，也能 import 到仓库根目录的 unitree_sdk2py。
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
"""05 前置摄像头：向 videohub 要一张 JPEG 照片。

VideoClient 不是"打开视频流"，而是 RPC：
    发一条请求（API 1001 GetImageSample）-> 回一帧 JPEG 的二进制。
所以它的速度取决于网络往返和机器人编码，不是摄像头标称帧率。

用法:
    python3 05_camera.py                    # 抓 1 张，存到 out/camera_shot.jpg
    python3 05_camera.py --frames 30        # 连抓 30 帧，测实际 FPS
    python3 05_camera.py --show             # 实时预览（需要 python3-opencv）

Ubuntu 装 OpenCV 用系统包，别用 pip（会把 numpy 升到 2.x，弄坏 ROS 2）：
    sudo apt install python3-opencv
"""
import argparse
import time
from pathlib import Path

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.video.video_client import VideoClient

OUT = Path(__file__).resolve().parent / "out"


def main():
    parser = argparse.ArgumentParser(description="Go2 前置摄像头抓拍")
    parser.add_argument("--iface", help="网卡名，如 eth0；不填则用 CYCLONEDDS_URI")
    parser.add_argument("--frames", type=int, default=1, help="抓取帧数，默认 1")
    parser.add_argument("--out", default=str(OUT / "camera_shot.jpg"), help="JPEG 保存路径")
    parser.add_argument("--show", action="store_true", help="实时预览，按 ESC 退出")
    args = parser.parse_args()

    if args.iface:
        ChannelFactoryInitialize(0, args.iface)
    else:
        ChannelFactoryInitialize(0)

    client = VideoClient()
    client.SetTimeout(3.0)
    client.Init()

    if args.show:
        try:
            import cv2
        except ImportError:
            print("没有 cv2。先 sudo apt install python3-opencv，或去掉 --show 只存文件。")
            return

    frames = 300 if (args.show and args.frames == 1) else args.frames
    saved = None
    count = 0
    t0 = time.monotonic()

    while count < frames:
        code, data = client.GetImageSample()
        if code != 0:
            print(f"取图失败 code={code}")
            print("常见原因：videohub 忙 / 机器人 App 正占用相机 / 网络超时。")
            return

        raw = bytes(data)
        saved = raw
        count += 1

        if args.show:
            import cv2
            import numpy as np

            image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
            if image is not None:
                cv2.imshow("Go2 front camera (ESC to quit)", image)
                if cv2.waitKey(20) == 27:
                    break

    elapsed = time.monotonic() - t0
    if saved is None:
        print("一帧都没拿到。")
        return

    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(saved)
    print(f"已保存 {path}（{len(saved) / 1024:.1f} KB）")
    if count > 1:
        print(f"抓了 {count} 帧，用时 {elapsed:.2f} s，约 {count / elapsed:.1f} FPS")
    if args.show:
        import cv2
        cv2.destroyAllWindows()

    print("\n课堂观察：同一帧既是'相机画面'，也是一段 JPEG 字节流。")
    print("把它和 04 的点云放在一起，就是最朴素的'感知输入'。")


if __name__ == "__main__":
    main()
