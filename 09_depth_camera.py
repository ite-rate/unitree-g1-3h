#!/usr/bin/env python3
"""09 深度相机：G1 头部的 Intel RealSense D435i，拍一张彩色图，量一个距离。

深度相机是什么传感器：
    普通相机只拍颜色；深度相机还能知道每个像素离相机多远。
    D435i 用两个红外摄像头像人的两只眼睛一样看同一个场景，
    同一个点在两幅图里的位置差越大，离得越近，由此算出每个像素的深度。
    所以它一次给两张图：彩色图（看起来是什么）+ 深度图（每个像素多远）。
    D435i 里还有一个自己的 IMU（本脚本不读）。

和前面的传感器最大的不同：数据不走 DDS 网络。
    相机用 USB 直接插在 G1 的开发计算单元（机器人身上的那台小电脑）上，
    所以本脚本要在那台电脑上运行，不是在你的笔记本上：
        ssh <用户名>@<开发计算单元的 IP>     # 地址以机器人现场标注为准
        python3 09_depth_camera.py
    需要那台电脑上装好 librealsense 和它的 Python 包 pyrealsense2。

本脚本做三件事：
    1. 打开彩色 + 深度两路图像，连续取 30 帧，量一下实际帧率；
    2. 打印画面正中心那个像素的距离；
    3. 把最后一帧彩色图存成 out/camera_color.jpg（有 OpenCV 时）。

用法:
    python3 09_depth_camera.py
    python3 09_depth_camera.py --frames 60

课堂演示：把手放在镜头正前方，慢慢前后移动，看"中心距离"跟着变。
         注意 D435i 太近（几十厘米以内）测不出深度，会显示 0。
"""
import argparse
import time
from pathlib import Path

import numpy as np

try:
    import pyrealsense2 as rs
except ImportError:
    rs = None

OUT = Path(__file__).resolve().parent / "out"
WIDTH, HEIGHT, FPS = 640, 480, 30


def main():
    parser = argparse.ArgumentParser(description="读 G1 头部 D435i 的彩色图和深度图")
    parser.add_argument("--frames", type=int, default=30, help="连续取多少帧")
    args = parser.parse_args()

    if rs is None:
        print("没找到 pyrealsense2。这个脚本要在 G1 的开发计算单元上运行，")
        print("并且那台电脑上要装好 librealsense（含 Python 包）。")
        return

    # 告诉相机要哪几路数据：深度图（每个像素是一个整数距离）和彩色图。
    pipe = rs.pipeline()
    cfg = rs.config()
    cfg.enable_stream(rs.stream.depth, WIDTH, HEIGHT, rs.format.z16, FPS)
    cfg.enable_stream(rs.stream.color, WIDTH, HEIGHT, rs.format.bgr8, FPS)
    try:
        profile = pipe.start(cfg)
    except RuntimeError as exc:
        print(f"打开相机失败: {exc}")
        print("检查：相机 USB 是否插好；有没有别的程序（如 realsense-viewer）正占用相机。")
        return

    # 深度图里存的是整数，乘以 depth_scale 才是米。
    depth_scale = profile.get_device().first_depth_sensor().get_depth_scale()

    try:
        t0 = time.monotonic()
        for _ in range(args.frames):
            frames = pipe.wait_for_frames()
        fps = args.frames / (time.monotonic() - t0)

        depth = frames.get_depth_frame()
        color = frames.get_color_frame()
        cx, cy = depth.get_width() // 2, depth.get_height() // 2
        center = depth.get_distance(cx, cy)  # 单位：米

        depth_img = np.asanyarray(depth.get_data()) * depth_scale
        valid = depth_img > 0  # 0 表示这个像素测不出深度（太近、反光、遮挡）

        print(f"实际帧率          约 {fps:.0f} 帧/秒")
        print(f"图像大小          {depth.get_width()} x {depth.get_height()}")
        print(f"画面中心距离      {center:.2f} m" + ("（0 = 测不出，可能太近）" if center == 0 else ""))
        if valid.any():
            print(f"整幅深度图        最近 {depth_img[valid].min():.2f} m，"
                  f"{valid.mean():.0%} 的像素有深度")

        try:
            import cv2
            OUT.mkdir(exist_ok=True)
            path = OUT / "camera_color.jpg"
            cv2.imwrite(str(path), np.asanyarray(color.get_data()))
            print(f"彩色图已保存      {path}")
        except ImportError:
            print("没装 OpenCV，跳过保存图片（sudo apt install python3-opencv）")
    finally:
        pipe.stop()


if __name__ == "__main__":
    main()
