# =============================================================================
# 课程阅读副本 · 官方源码，逻辑未改动，只加了注释
# 上游: unitree_sdk2_python（unitree-robotics/unitree_sdk2_python）
# 版本: 814556d15970dd2ecf1c9984e845ca02ab07e206
# 本文件: unitree_sdk2py/g1/audio/g1_audio_api.py
# 课程位置: 04_audio_led.py
#
# ▶ G1 语音/灯（服务名 "voice"）的常量表。
#   服务端 topic：rt/api/voice/request（ROS 2 里叫 /api/voice/request）。
#
# ▶ API 编号总表（编号 / 作用 / 参数 / 返回）
#   1001  TTS  文字转语音     {"index":0, "text":"...", "speaker_id":0}    code
#   1002  ASR  语音识别       本课不用                                  code
#   1003  开始播放 PCM 流      JSON(app_name,stream_id) + 二进制 PCM      code
#   1004  停止播放            {"app_name":"..."}                        恒返回 0
#   1005  读音量              {}                                        (code, {"volume":0-100})
#   1006  设音量              {"volume":0-100}                          code
#   1010  设 RGB 灯带         {"R":0-255,"G":0-255,"B":0-255}           code
#   1007–1009 官方 Python 文件里没定义，固件可能有其他用途。
# =============================================================================

"""
" service name
"""
AUDIO_SERVICE_NAME = "voice"

"""
" service api version
"""
AUDIO_API_VERSION = "1.0.0.0"

"""
" api id
"""
ROBOT_API_ID_AUDIO_TTS = 1001            # 文字转语音
ROBOT_API_ID_AUDIO_ASR = 1002            # 语音识别（本课不用）
ROBOT_API_ID_AUDIO_START_PLAY = 1003     # 开始播放 PCM 流
ROBOT_API_ID_AUDIO_STOP_PLAY = 1004      # 停止播放
ROBOT_API_ID_AUDIO_GET_VOLUME = 1005     # 读音量
ROBOT_API_ID_AUDIO_SET_VOLUME = 1006     # 设音量 0–100
ROBOT_API_ID_AUDIO_SET_RGB_LED = 1010    # 设灯带 RGB 0–255

"""
" error code
"""
# ▶ 返回码（和 sport/arm 服务同一套 RPC 错误码）
#   0      成功
#   3102   请求没发出去（网卡 / DDS 配置）
#   3104   等回复超时（机器人没在听）
#   3203   固件没实现这个接口（型号 / 版本不支持）
#   3204   参数不对（音量 0–100，RGB 0–255）
