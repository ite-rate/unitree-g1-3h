# =============================================================================
# 课程阅读副本 · 官方源码，逻辑未改动，只加了注释
# 上游: https://github.com/unitreerobotics/unitree_sdk2_python
# 版本: 814556d15970dd2ecf1c9984e845ca02ab07e206（与 scripts/install.sh 固定的一致）
# 本文件: unitree_sdk2py/go2/video/video_client.py
# 课程位置: 05_camera.py / 07_demo_show.py
#
# ▶ GetImageSample 走的是 _CallBinary，返回 (code, bytes)。
#   bytes 就是一张完整 JPEG 的原始字节，没有时间戳、没有帧号。
#   所以“帧率”完全取决于你调用它的频率；保存时直接 write_bytes 就是 .jpg。
#   想看画面要自己 cv2.imdecode，SDK 不解码、不显示。
# =============================================================================
import json

from ...rpc.client import Client
from .video_api import *


"""
" class VideoClient
"""
class VideoClient(Client):
    def __init__(self):
        super().__init__(VIDEO_SERVICE_NAME, False)


    def Init(self):
        # set api version
        self._SetApiVerson(VIDEO_API_VERSION)
        # regist api
        self._RegistApi(VIDEO_API_ID_GETIMAGESAMPLE, 0)

    # 1001
    def GetImageSample(self):
        return self._CallBinary(VIDEO_API_ID_GETIMAGESAMPLE, [])
