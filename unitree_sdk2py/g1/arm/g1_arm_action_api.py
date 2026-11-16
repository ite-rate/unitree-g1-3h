# =============================================================================
# 课程阅读副本 · 官方源码，逻辑未改动，只加了注释
# 上游: unitree_sdk2_python（unitree-robotics/unitree_sdk2_python）
# 版本: 814556d15970dd2ecf1c9984e845ca02ab07e206
# 本文件: unitree_sdk2py/g1/arm/g1_arm_action_api.py
# 课程位置: 03_arm_actions.py
#
# ▶ G1 手臂动作（服务名 "arm"）的常量表。
#   服务端 topic：rt/api/arm/request（ROS 2 里叫 /api/arm/request）。
#
# ▶ 注意：这里的 7106 和运控里的 7106 数字相同，但属于两个不同服务：
#       运控 7106 = SetTaskId（sport 服务，挥手/握手）
#       手臂 7106 = ExecuteAction（arm 服务，16 个预置动作）
#   区分它们靠的是服务名，不是 API ID。
# =============================================================================

"""
" service name
"""
ARM_ACTION_SERVICE_NAME = "arm"

"""
" service api version
"""
ARM_ACTION_API_VERSION = "1.0.0.14"

"""
" api id
"""
ROBOT_API_ID_ARM_ACTION_EXECUTE_ACTION = 7106   # 执行一个动作，参数 {"data": action_id}
ROBOT_API_ID_ARM_ACTION_GET_ACTION_LIST = 7107  # 问机器人支持哪些动作，回 JSON

"""
" error code
"""
# ▶ 返回码（来自 unitree_ros2 的 g1_arm_action_client.hpp）
#   0      成功
#   7400   rt/armsdk 被占用：有别的进程正在控手臂
#   7401   手臂正持有上一个动作：先发 99 release arm，或重复同一个 action_id
#   7402   action_id 非法：对照 g1_arm_action_client.py 的 action_map
#   7404   当前 FSM 不支持手臂动作：只支持 FSM {500, 501, 801}；
#          在 801 下还要求 fsm mode 是 {0, 3}
#   3102   请求没发出去（网卡 / DDS 配置）
#   3104   等回复超时（机器人没在听）
#
# ▶ 动作 ID 总表见 g1_arm_action_client.py 顶部注释。
