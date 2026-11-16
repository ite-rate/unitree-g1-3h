# =============================================================================
# 课程阅读副本 · 官方源码，逻辑未改动，只加了注释
# 上游: https://github.com/unitreerobotics/unitree_sdk2_python
# 版本: 814556d15970dd2ecf1c9984e845ca02ab07e206（与 scripts/install.sh 固定的一致）
# 本文件: unitree_sdk2py/go2/vui/vui_api.py
# 课程位置: 03_light_volume.py / 07_demo_show.py
#
# ▶ VUI = 灯 + 音量那一套。
#   1003/1004 = 设/读音量，1005/1006 = 设/读亮度，范围都是 0–10。
#   ▶ 注意：vui_client.py 里 GetVolume 上方注释写的是 "# 1006"，那是上游笔误，
#     实际常量是 1004。以本文件为准。
# =============================================================================
"""
" service name
"""
VUI_SERVICE_NAME = "vui"


"""
" service api version
"""
VUI_API_VERSION = "1.0.0.1"


"""
" api id
"""
VUI_API_ID_SETSWITCH = 1001
VUI_API_ID_GETSWITCH = 1002
VUI_API_ID_SETVOLUME = 1003
VUI_API_ID_GETVOLUME = 1004
VUI_API_ID_SETBRIGHTNESS = 1005
VUI_API_ID_GETBRIGHTNESS = 1006
