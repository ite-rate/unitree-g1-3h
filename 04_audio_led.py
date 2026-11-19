#!/usr/bin/env python3
"""04 G1 语音与灯：TTS、音量、RGB 灯带。

接口是 AudioClient，四件事放一个 client 里：
    TtsMaker(text, speaker_id)      机器人自己念
    GetVolume() / SetVolume(v)     音量 0-100
    LedControl(R, G, B)            灯带颜色 0-255

TTS 是机器人自己念，不是播放你电脑上的音频。
（PlayStream 也能播 wav，但只认 16 kHz / 单声道 / 16-bit PCM：
    ffmpeg -i in.wav -ar 16000 -ac 1 -sample_fmt s16 out.wav）

用法:
    python3 04_audio_led.py --get
    python3 04_audio_led.py --volume 80
    python3 04_audio_led.py --tts "大家好，我是 G1"
    python3 04_audio_led.py --led 0 128 255
    python3 04_audio_led.py --demo
"""
import argparse
import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient


def main():
    parser = argparse.ArgumentParser(description="G1 语音、音量、灯带")
    parser.add_argument("--get", action="store_true", help="读当前音量")
    parser.add_argument("--volume", type=int, help="设置音量 0-100")
    parser.add_argument("--tts", help="让机器人念一段文字")
    parser.add_argument("--led", nargs=3, type=int, metavar=("R", "G", "B"), help="灯带颜色 0-255")
    parser.add_argument("--demo", action="store_true", help="音量 + TTS + 红绿蓝灯循环")
    args = parser.parse_args()

    if not any([args.get, args.volume is not None, args.tts, args.led, args.demo]):
        parser.print_help()
        return
    if args.volume is not None and not 0 <= args.volume <= 100:
        print("音量范围是 0-100。")
        return
    if args.led and any(not 0 <= v <= 255 for v in args.led):
        print("RGB 每个分量范围是 0-255。")
        return

    ChannelFactoryInitialize(0)
    client = AudioClient()
    client.SetTimeout(10.0)
    client.Init()

    if args.get:
        code, data = client.GetVolume()
        print(f"GetVolume -> code={code}, 当前音量 {data.get('volume') if data else '?'}")

    if args.volume is not None:
        print(f"SetVolume({args.volume}) ->", client.SetVolume(args.volume),
              "（非 0：先关掉手机 App 的占用）")

    if args.tts:
        print(f'TtsMaker("{args.tts}") ->', client.TtsMaker(args.tts, 0),
              "（没声音：--volume 80 再试一次）")
        time.sleep(1.0)

    if args.led:
        r, g, b = args.led
        print(f"LedControl({r}, {g}, {b}) ->", client.LedControl(r, g, b))

    if args.demo:
        print("SetVolume(80) ->", client.SetVolume(80))
        print("TtsMaker ->", client.TtsMaker("大家好，我是宇树 G1。现在测试语音和灯带。", 0))
        time.sleep(6.0)
        for color in ((255, 0, 0), (0, 255, 0), (0, 0, 255)):
            print(f"LedControl{color} ->", client.LedControl(*color))
            time.sleep(1.0)
        print("LedControl(0,0,0) ->", client.LedControl(0, 0, 0))
        print("TtsMaker ->", client.TtsMaker("测试完毕，谢谢。", 0))


if __name__ == "__main__":
    main()
