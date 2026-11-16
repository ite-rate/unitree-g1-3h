# =============================================================================
# 课程阅读副本 · 官方源码，逻辑未改动，只加了注释
# 上游: unitree_sdk2_python（unitree-robotics/unitree_sdk2_python）
# 版本: 814556d15970dd2ecf1c9984e845ca02ab07e206
# 本文件: unitree_sdk2py/g1/audio/g1_audio_client.py
# 课程位置: 04_audio_led.py
#
# ▶ G1 语音与灯带的客户端：TTS、音量、RGB、播放 wav。
#   服务名 "voice" -> DDS topic rt/api/voice/request。
#
# ▶ 参数范围（超出会返回 3204 或被固件忽略）
#   SetVolume   0–100
#   LedControl  R/G/B 各 0–255
#   TtsMaker    speaker_id 音色编号，0 是默认；其他值以固件为准
#   PlayStream  只接受 16 kHz / 单声道 / 16-bit PCM
# =============================================================================
import json

from ...rpc.client import Client
from .g1_audio_api import *

"""
" class SportClient
"""
class AudioClient(Client):
    def __init__(self):
        super().__init__(AUDIO_SERVICE_NAME, False)
        # TTS 序号，本意是每念一句 +1；实际下面的写法有 bug，见 TtsMaker。
        self.tts_index = 0

    def Init(self):
        # set api version
        self._SetApiVerson(AUDIO_API_VERSION)

        # regist api
        self._RegistApi(ROBOT_API_ID_AUDIO_TTS, 0)
        self._RegistApi(ROBOT_API_ID_AUDIO_ASR, 0)
        self._RegistApi(ROBOT_API_ID_AUDIO_START_PLAY, 0)
        self._RegistApi(ROBOT_API_ID_AUDIO_STOP_PLAY, 0)
        self._RegistApi(ROBOT_API_ID_AUDIO_GET_VOLUME, 0)
        self._RegistApi(ROBOT_API_ID_AUDIO_SET_VOLUME, 0) 
        self._RegistApi(ROBOT_API_ID_AUDIO_SET_RGB_LED, 0) 

    ## API Call ##
    def TtsMaker(self, text: str, speaker_id: int):
        # ▶ 上游 bug：这里写的是 += 自己，不是 += 1。
        #   0 + 0 永远是 0，所以 index 恒为 0。不影响"念一句话"，
        #   但如果固件用 index 区分多句 TTS，可能会有覆盖问题。
        #   课程里不改官方代码，只在这里标出来。
        self.tts_index += self.tts_index
        p = {}
        p["index"] = self.tts_index
        p["text"] = text
        p["speaker_id"] = speaker_id
        parameter = json.dumps(p)
        code, data = self._Call(ROBOT_API_ID_AUDIO_TTS, parameter)
        return code

    def GetVolume(self):
        # ▶ 返回 (code, dict)，dict 形如 {"volume": 85}。
        p = {}
        parameter = json.dumps(p)
        code, data = self._Call(ROBOT_API_ID_AUDIO_GET_VOLUME, parameter)
        if code == 0:
            return code, json.loads(data)
        else:
            return code, None

    def SetVolume(self, volume: int):
        # ▶ volume 0–100。0 是静音。
        p = {}
        p["volume"] = volume
        parameter = json.dumps(p)
        code, data = self._Call(ROBOT_API_ID_AUDIO_SET_VOLUME, parameter)
        return code

    def LedControl(self, R: int, G: int, B: int):
        # ▶ 灯带颜色，每个分量 0–255。(0,0,0) 是关灯。
        p = {}
        p["R"] = R
        p["G"] = G
        p["B"] = B
        parameter = json.dumps(p)
        code, data = self._Call(ROBOT_API_ID_AUDIO_SET_RGB_LED, parameter)
        return code
    
    def PlayStream(self, app_name: str, stream_id: str, pcm_data: bytes):
        # ▶ 播放一段裸 PCM。JSON 参数和二进制 PCM 分两段发。
        #   格式必须 16 kHz / 单声道 / 16-bit little-endian。
        #   传错格式不会报错，只会没声音——所以课程脚本先自己检查 wav。
        param = json.dumps({"app_name": app_name, "stream_id": stream_id})
        pcm_list = list(pcm_data) 
        return self._CallRequestWithParamAndBin(ROBOT_API_ID_AUDIO_START_PLAY, param, pcm_list)
    
    def PlayStop(self, app_name: str):
        # ▶ 停止播放。注意：上游忽略了 _Call 的返回码，无条件 return 0，
        #   所以这里返回 0 不代表机器人真的停了。课堂只用它做收尾。
        parameter = json.dumps({"app_name": app_name})
        self._Call(ROBOT_API_ID_AUDIO_STOP_PLAY, parameter)
        return 0
