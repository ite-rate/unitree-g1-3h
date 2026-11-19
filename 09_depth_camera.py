#!/usr/bin/env python3
"""09 深度相机：G1 头部的 Intel RealSense D435i。

D435i 用两个红外摄像头像人的两只眼睛一样看同一个场景，算出每个像素的距离，
所以一次给两张图：彩色图（看起来是什么）+ 深度图（每个像素多远）。

★ 想直接"看"实时画面，用官方查看器（就在相机插着的那台电脑上跑）：
        realsense-viewer
    左边彩色、右边深度，实时刷新，还能录 bag。不用写任何代码。
本脚本是它的 SDK 写法：量帧率、报画面中心的距离。

相机 USB 插在 G1 的开发计算单元上，不走网络，所以要在那台电脑上运行：
        ssh <用户名>@<开发计算单元 IP>     # 地址以现场标注为准
        python3 09_depth_camera.py
    （那台电脑要装好 librealsense 及其 Python 包 pyrealsense2）

课堂演示：把手放在镜头正前方前后移动，看中心距离跟着变。
         注意 D435i 太近（几十厘米内）测不出深度，会显示 0。
"""
import time
from pathlib import Path

import numpy as np
import pyrealsense2 as rs

if __name__ == "__main__":
    # 告诉相机要哪两路数据：深度图 + 彩色图，640x480 @ 30fps
    pipe = rs.pipeline()
    cfg = rs.config()
    cfg.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    cfg.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

    try:
        pipe.start(cfg)
    except RuntimeError as exc:
        print(f"打开相机失败: {exc}")
        print("检查：USB 插好没；有没有别的程序（如 realsense-viewer）正占用相机。")
        raise SystemExit(1)

    try:
        t0 = time.monotonic()
        frames = None
        for _ in range(30):
            frames = pipe.wait_for_frames()   # 阻塞等一帧
        print(f"实际帧率约 {30 / (time.monotonic() - t0):.0f} 帧/秒")

        depth = frames.get_depth_frame()
        cx, cy = depth.get_width() // 2, depth.get_height() // 2
        center = depth.get_distance(cx, cy)   # 画面正中心的距离，单位米
        print(f"画面中心距离 {center:.2f} m" +
              ("（0 = 测不出，可能太近）" if center == 0 else ""))

        # 有 OpenCV 就顺手存一张彩色图（官方例程的标准三行）
        try:
            import cv2
            color = np.asanyarray(frames.get_color_frame().get_data())
            out = Path("out")
            out.mkdir(exist_ok=True)
            cv2.imwrite(str(out / "camera_color.jpg"), color)
            print(f"彩色图已保存 out/camera_color.jpg")
        except ImportError:
            print("没装 OpenCV（sudo apt install python3-opencv），跳过保存图片")
    finally:
        pipe.stop()
