#!/usr/bin/env python3
# 附加章节：Go2 版本。保留原脚本，逻辑未改，只补了下面 3 行路径引导，
# 这样从 go2/ 目录直接运行时，也能 import 到仓库根目录的 unitree_sdk2py。
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
"""03 灯与声音：调头部 LED 亮度、调音量。

Go2 的 SDK 里，这一块叫 VUI（Voice UI），服务名 "vui"：
    SetBrightness / GetBrightness   头部白色 LED，0~10 档
    SetVolume / GetVolume           内置语音/提示音音量，0~10 档
    SetSwitch / GetSwitch           VUI 总开关

注意：这版 SDK 的 Go2 接口没有"播放任意音频文件"的 client。
声音来自机器人内置提示音和动作音效，我们只能调音量。
（G1 另有 AudioClient，可以 TTS / 播放 wav，不在这节课范围。）

用法:
    python3 03_light_volume.py --get
    python3 03_light_volume.py --brightness 10
    python3 03_light_volume.py --volume 3
    python3 03_light_volume.py --demo
"""
import argparse
import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.vui.vui_client import VuiClient


def check(code, action):
    if code == 0:
        print(f"  {action}: 成功")
    else:
        print(f"  {action}: 失败 code={code}（VUI 服务不可用，或参数超范围）")
    return code == 0


def main():
    parser = argparse.ArgumentParser(description="Go2 头部 LED 亮度与音量")
    parser.add_argument("--iface", help="网卡名，如 eth0；不填则用 CYCLONEDDS_URI")
    parser.add_argument("--brightness", type=int, help="LED 亮度 0~10")
    parser.add_argument("--volume", type=int, help="音量 0~10")
    parser.add_argument("--get", action="store_true", help="只读取当前值")
    parser.add_argument("--demo", action="store_true", help="从暗到亮、从静音到最大，再恢复")
    args = parser.parse_args()

    for name, value in (("brightness", args.brightness), ("volume", args.volume)):
        if value is not None and not 0 <= value <= 10:
            print(f"{name} 必须在 0~10 之间。")
            return

    if args.iface:
        ChannelFactoryInitialize(0, args.iface)
    else:
        ChannelFactoryInitialize(0)

    client = VuiClient()
    client.SetTimeout(3.0)
    client.Init()

    print("读取当前值：")
    code, level = client.GetBrightness()
    print(f"  GetBrightness -> code={code}, level={level}")
    code, level = client.GetVolume()
    print(f"  GetVolume     -> code={code}, level={level}")

    if args.brightness is not None:
        check(client.SetBrightness(args.brightness), f"SetBrightness({args.brightness})")

    if args.volume is not None:
        check(client.SetVolume(args.volume), f"SetVolume({args.volume})")

    if args.demo:
        print("\n亮度 0 -> 3 -> 6 -> 10（看头部白光）")
        for level in (0, 3, 6, 10):
            check(client.SetBrightness(level), f"SetBrightness({level})")
            time.sleep(0.8)

        print("\n音量 0 -> 3 -> 6 -> 10（听内置提示音）")
        for level in (0, 3, 6, 10):
            check(client.SetVolume(level), f"SetVolume({level})")
            time.sleep(0.8)

        print("\n恢复亮度 5、音量 5")
        client.SetBrightness(5)
        client.SetVolume(5)


if __name__ == "__main__":
    main()
