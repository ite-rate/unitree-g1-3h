# =============================================================================
# 课程阅读副本 · 官方源码，逻辑未改动，只加了注释
# 上游: unitree_sdk2_python（unitree-robotics/unitree_sdk2_python）
# 版本: 814556d15970dd2ecf1c9984e845ca02ab07e206
# 本文件: unitree_sdk2py/g1/loco/g1_loco_api.py
# 课程位置: 02_loco.py
#
# ▶ 这个文件是 G1 运控（服务名 "sport"）的常量表：
#   服务名、API 版本、请求编号、内部状态机模式。真正的网络调用在
#   g1_loco_client.py，这里只有数字。
#
# ▶ 读法：G1 的运控不是"一个动作一个 API"，而是"切状态机（FSM）"。
#   所有站、蹲、坐、走都通过 7101 SetFsmId 切到不同 FSM，再通过
#   7105 SetVelocity 给速度。SDK 的 Damp()/Start()/Sit() 只是把
#   SetFsmId(x) 包了一层。
# =============================================================================
from enum import IntEnum

"""
" service name
"""
LOCO_SERVICE_NAME = "sport"


"""
" service api version
"""
LOCO_API_VERSION = "1.0.0.0"


"""
" api id
"""
# ▶ 读状态（7001–7006）：只发请求、不带参数，机器人回 JSON。
ROBOT_API_ID_LOCO_GET_FSM_ID = 7001        # 当前 FSM 编号，最常用
ROBOT_API_ID_LOCO_GET_FSM_MODE = 7002      # 内部状态机模式，见 InternalFsmMode
ROBOT_API_ID_LOCO_GET_BALANCE_MODE = 7003  # 平衡模式
ROBOT_API_ID_LOCO_GET_SWING_HEIGHT = 7004  # 抬腿高度
ROBOT_API_ID_LOCO_GET_STAND_HEIGHT = 7005  # 站立高度
ROBOT_API_ID_LOCO_GET_PHASE = 7006 # deprecated  # 已废弃，别在新代码里用

# ▶ 写状态（7101–7111）：参数放在 JSON 的 "data" 字段里。
ROBOT_API_ID_LOCO_SET_FSM_ID = 7101        # 切状态机，站/蹲/坐都靠它
ROBOT_API_ID_LOCO_SET_BALANCE_MODE = 7102  # 切平衡模式
ROBOT_API_ID_LOCO_SET_SWING_HEIGHT = 7103  # 设抬腿高度
ROBOT_API_ID_LOCO_SET_STAND_HEIGHT = 7104  # 设站立高度（0 = 最低，0xFFFFFFFF = 最高）
ROBOT_API_ID_LOCO_SET_VELOCITY = 7105      # 给速度 [vx, vy, omega] + duration
ROBOT_API_ID_LOCO_SET_ARM_TASK = 7106      # 挥手/握手这类"任务 ID"
ROBOT_API_ID_LOCO_SET_SPEED_MODE = 7107    # 速度档位
ROBOT_API_ID_LOCO_SWITCH_TO_USER_CTRL = 7110   # 把控制权交给用户程序
ROBOT_API_ID_LOCO_SWITCH_TO_INTERNAL_CTRL = 7111  # 还给内部运控


class InternalFsmMode(IntEnum):
    # ▶ 7002/7111 用的模式值。
    #   LAST      保持上一次的模式（切回内部运控时常用）
    #   PASSIVE   被动：关节不主动出力，类似阻尼
    #   WALKRUN   行走/奔跑
    LAST = 0
    PASSIVE = 1
    WALKRUN = 2


"""
" error code
"""
# ▶ 返回码（来自 unitree_ros2 的 g1_loco_client.hpp，Python 文件里没写全）
#   0      成功
#   3102   请求没发出去（网卡 / DDS 配置问题）
#   3104   等机器人回复超时（机器人没在听，或当前状态不允许）
#   3203   机器人固件没实现这个接口（型号 / 版本不支持）
#   3204   参数不对
#   7301   LocoState 不可用（运控服务没起来）
#   7302   FSM ID 非法（这个机型不支持该状态）
#   7303   Task ID 非法（挥手 / 握手的参数不对）
#
# ▶ FSM 编号总表（“名字 / ID / 机器人做什么 / 触发方法 / 风险”）
#   名字              ID    机器人做什么                     触发方法              风险
#   zero_torque        0    零力矩，关节立刻失去支撑，会软倒  SetFsmId(0)           高
#   damp               1    阻尼保护，关节变硬但不保持姿态    SetFsmId(1) / Damp()  低
#   squat              2    蹲下                              SetFsmId(2)           低
#   sit                3    坐下                              SetFsmId(3) / Sit()   低
#   stand_up           4    从坐/蹲站起                       SetFsmId(4)           低
#   start            500    进入主运控                        SetFsmId(500)/Start() 低
#   lie2standup      702    从仰躺站起（要求仰面、硬平地）     SetFsmId(702)         高
#   squat2standup    706    从蹲姿站起                        SetFsmId(706)         低
#   standup2squat    706    上游与 squat2standup 共用 706      SetFsmId(706)         低
#
# ▶ 注意：Python 版没有 Squat()/StandUp() 封装（C++ 版有，ID 分别是 2、4），
#   所以课程里直接用 SetFsmId(2) / SetFsmId(4)。
