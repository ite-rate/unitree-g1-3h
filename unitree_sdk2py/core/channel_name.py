# =============================================================================
# 课程阅读副本 · 官方源码，逻辑未改动，只加了注释
# 上游: https://github.com/unitreerobotics/unitree_sdk2_python
# 版本: 814556d15970dd2ecf1c9984e845ca02ab07e206（与 scripts/install.sh 固定的一致）
# 本文件: unitree_sdk2py/core/channel_name.py
# 课程位置: 02_actions.py / 03_light_volume.py / 05_camera.py（间接）
#
# ▶ RPC 的 channel 命名规则：rt/api/<service>/request 和 .../response。
#   sport → rt/api/sport/request，vui → rt/api/vui/request，
#   videohub → rt/api/videohub/request。
#   在 ros2 topic list 里会显示成 /api/sport/request 这种名字。
#   所以“SDK 调用”和“ROS 2 topic”在底层是同一条 DDS 总线，不是两套东西。
# =============================================================================
from enum import Enum

"""
" Enum ChannelType
"""
class ChannelType(Enum):
    SEND = 0
    RECV = 1

"""
" function GetClientChannelName
"""
def GetClientChannelName(serviceName: str, channelType: ChannelType):
    name = "rt/api/" + serviceName
    
    if channelType == ChannelType.SEND:
        name += "/request"
    else:
        name += "/response"

    return name

"""
" function GetClientChannelName
"""
def GetServerChannelName(serviceName: str, channelType: ChannelType):
    name = "rt/api/" + serviceName
    
    if channelType == ChannelType.SEND:
        name += "/response"
    else:
        name += "/request"

    return name