#!/usr/bin/env python3
"""04 G1 语音与灯：TTS、音量、RGB 灯带、播放 wav。

接口是 AudioClient，服务名 "voice"，底层 topic 是 rt/api/voice/request。
它把四件事放在一个 client 里：
    TtsMaker(text, speaker_id)   文字转语音，机器人自己念
    GetVolume() / SetVolume(v)   音量，0–100
    LedControl(R, G, B)          灯带颜色，0–255
    PlayStream / PlayStop        播放 16 kHz 单声道 16-bit PCM

▶ 上游已知小 bug：TtsMaker 里写的是 self.tts_index += self.tts_index
  （自乘而不是自增），所以 index 恒为 0。不影响本课使用，但读源码时会看到。

▶ PlayStream 只接受 16 kHz / 单声道 / 16-bit PCM 的 wav。
  采样率或声道不对，机器人不会报错，只会没声音，所以脚本先自己检查。

用法:
    python3 04_audio_led.py --get
    python3 04_audio_led.py --volume 80
    python3 04_audio_led.py --tts "大家好，我是 G1"
    python3 04_audio_led.py --led 0 128 255
    python3 04_audio_led.py --wav path/to/test.wav
    python3 04_audio_led.py --demo
"""
import argparse
import time
from pathlib import Path

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient

# G1 只认这个格式：16 kHz、单声道、16-bit PCM。
WAV_RATE = 16000
WAV_CHANNELS = 1
WAV_BITS = 16

AUDIO_ERRORS = {
    3102: "请求没发出去（网卡 / DDS 配置）",
    3104: "等回复超时（机器人没在听）",
    3203: "固件没有实现这个接口（型号 / 版本不支持）",
    3204: "参数不对（音量 0–100，LED 0–255）",
}


def explain(code):
    print(f"  -> code = {code}")
    if code == 0:
        print("  成功。")
    elif code in AUDIO_ERRORS:
        print(f"  失败：{AUDIO_ERRORS[code]}")
    else:
        print("  失败：非 0。先确认机器人没被 App 占用。")


def read_wav(path: str):
    """只解析标准 PCM wav，返回 (pcm_bytes, sample_rate, channels, bits)。

    不依赖 scipy / soundfile，避免把 ROS 2 Humble 的 numpy 弄坏。
    解析方式：从头遍历 RIFF 的 chunk，找 "fmt " 和 "data"。
    """
    data = Path(path).read_bytes()
    if len(data) < 12 or data[0:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("不是 RIFF/WAVE 文件")

    pos = 12
    fmt = None
    pcm = None
    while pos + 8 <= len(data):
        chunk_id = data[pos:pos + 4]
        size = int.from_bytes(data[pos + 4:pos + 8], "little")
        body = data[pos + 8:pos + 8 + size]

        if chunk_id == b"fmt " and len(body) >= 16:
            fmt = {
                "audio_format": int.from_bytes(body[0:2], "little"),
                "channels": int.from_bytes(body[2:4], "little"),
                "sample_rate": int.from_bytes(body[4:8], "little"),
                "bits": int.from_bytes(body[14:16], "little"),
            }
        elif chunk_id == b"data":
            pcm = body

        pos += 8 + size + (size & 1)  # chunk 按 2 字节对齐

    if fmt is None or pcm is None:
        raise ValueError("缺 fmt 或 data chunk")
    if fmt["audio_format"] != 1:
        raise ValueError(f"不是 PCM（audio_format={fmt['audio_format']}）")
    return pcm, fmt["sample_rate"], fmt["channels"], fmt["bits"]


def play_wav(client, path: str):
    pcm, rate, channels, bits = read_wav(path)
    print(f"  wav: {rate} Hz / {channels} 声道 / {bits} bit / {len(pcm) / 1024:.1f} KB")
    if (rate, channels, bits) != (WAV_RATE, WAV_CHANNELS, WAV_BITS):
        print(f"  拒绝播放：G1 只接受 {WAV_RATE} Hz / {WAV_CHANNELS} 声道 / {WAV_BITS} bit")
        print("  转换命令（ffmpeg）:")
        print(f"    ffmpeg -i {path} -ar 16000 -ac 1 -sample_fmt s16 out.wav")
        return

    app_name = "course"
    stream_id = str(int(time.time() * 1000))
    print(f"  PlayStream(app={app_name}, stream={stream_id})")
    explain(client.PlayStream(app_name, stream_id, pcm))
    time.sleep(3.0)  # 给机器人 3 秒把缓冲播完
    print(f"  PlayStop({app_name})")
    client.PlayStop(app_name)


def main():
    parser = argparse.ArgumentParser(description="G1 语音、音量、灯带")
    parser.add_argument("--get", action="store_true", help="读当前音量")
    parser.add_argument("--volume", type=int, help="设置音量 0–100")
    parser.add_argument("--tts", help="让机器人念一段文字")
    parser.add_argument("--speaker", type=int, default=0, help="TTS 音色编号，默认 0（以固件为准）")
    parser.add_argument("--led", nargs=3, type=int, metavar=("R", "G", "B"), help="灯带颜色 0–255")
    parser.add_argument("--wav", help="播放 16 kHz 单声道 16-bit wav")
    parser.add_argument("--demo", action="store_true", help="音量 + TTS + 灯带循环")
    parser.add_argument("--iface", help="网卡名，如 eth0；不填则用 CYCLONEDDS_URI")
    args = parser.parse_args()

    if not any([args.get, args.volume is not None, args.tts, args.led, args.wav, args.demo]):
        parser.print_help()
        return

    if args.volume is not None and not 0 <= args.volume <= 100:
        print("音量范围是 0–100。")
        return
    if args.led and any(not 0 <= v <= 255 for v in args.led):
        print("RGB 每个分量范围是 0–255。")
        return

    if args.iface:
        ChannelFactoryInitialize(0, args.iface)
    else:
        ChannelFactoryInitialize(0)

    client = AudioClient()
    client.SetTimeout(10.0)
    client.Init()

    if args.get:
        code, data = client.GetVolume()
        print(f"GetVolume -> code={code}, data={data}")
        if code == 0 and data:
            print(f"  当前音量: {data.get('volume')}")

    if args.volume is not None:
        print(f"[SetVolume({args.volume})]")
        explain(client.SetVolume(args.volume))

    if args.tts:
        print(f'[TtsMaker] "{args.tts}" speaker_id={args.speaker}')
        explain(client.TtsMaker(args.tts, args.speaker))
        time.sleep(1.0)

    if args.led:
        r, g, b = args.led
        print(f"[LedControl({r}, {g}, {b})]")
        explain(client.LedControl(r, g, b))

    if args.wav:
        try:
            play_wav(client, args.wav)
        except Exception as exc:  # 文件读不了就明确告诉学生，不要静默失败
            print(f"  读取 wav 失败: {exc}")

    if args.demo:
        print("\n===== demo: 音量 80 -> TTS -> 红绿蓝 =====")
        explain(client.SetVolume(80))
        explain(client.TtsMaker("大家好，我是宇树 G1。现在测试语音和灯带。", 0))
        time.sleep(6.0)
        for color in ((255, 0, 0), (0, 255, 0), (0, 0, 255)):
            print(f"[LedControl{color}]")
            explain(client.LedControl(*color))
            time.sleep(1.0)
        explain(client.LedControl(0, 0, 0))
        explain(client.TtsMaker("测试完毕，谢谢。", 0))


if __name__ == "__main__":
    main()
