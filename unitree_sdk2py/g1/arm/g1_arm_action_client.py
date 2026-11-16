# =============================================================================
# 课程阅读副本 · 官方源码，逻辑未改动，只加了注释
# 上游: unitree_sdk2_python（unitree-robotics/unitree_sdk2_python）
# 版本: 814556d15970dd2ecf1c9984e845ca02ab07e206
# 本文件: unitree_sdk2py/g1/arm/g1_arm_action_client.py
# 课程位置: 03_arm_actions.py
#
# ▶ G1 手臂预置动作客户端。一个 action_id 就是一条固件里编好的轨迹，
#   你的程序只负责发编号，不负责算关节角。
#
# ▶ 动作枚举总表（名字 / ID / 中文 / 机器人做什么 / 触发方法 / 风险）
#   名字              ID   中文            机器人做什么              触发方法                    风险
#   release arm       99   释放手臂        收回手臂，保持型动作收尾   ExecuteAction(99)           低
#   two-hand kiss     11   双手飞吻        双手比飞吻                 ExecuteAction(11)           低
#   left kiss         12   左手飞吻        左手比飞吻                 ExecuteAction(12)           低
#   right kiss        13   右手飞吻        右手比飞吻                 ExecuteAction(13)           低
#   hands up          15   双手举起        双臂上举，重心会变         ExecuteAction(15)           中
#   clap              17   拍手            双手拍手                   ExecuteAction(17)           低
#   high five         18   举手击掌        举起一只手等人击掌         ExecuteAction(18)           中
#   hug               19   拥抱            双臂张开做拥抱姿势         ExecuteAction(19)           中
#   heart             20   比心            双手比心                   ExecuteAction(20)           中
#   right heart       21   右手比心        右手比心                   ExecuteAction(21)           中
#   reject            22   拒绝            摆手拒绝                   ExecuteAction(22)           低
#   right hand up     23   举右手          只举右手                   ExecuteAction(23)           低
#   x-ray           24   双手交叉        双臂交叉成 X               ExecuteAction(24)           低
#   face wave         25   脸旁挥手        手在脸旁挥动               ExecuteAction(25)           低
#   high wave         26   高举挥手        手举高挥动                 ExecuteAction(26)           低
#   shake hand        27   握手            伸手保持握手姿势           ExecuteAction(27)           中
#
# ▶ "保持型"（15/18/19/20/21/27）做完不会自动收回，课程脚本默认补 99。
#
# ▶ 执行条件（否则返回 7404）：
#   FSM 必须是 500 / 501 / 801；在 801 下还要求 fsm mode 是 {0, 3}。
#   不知道当前 FSM？用 LocoClient.GetFsmId() 查（02_loco.py 里有）。
# =============================================================================
import json

from ...rpc.client import Client
from .g1_arm_action_api import *

# ▶ 名字必须和这里完全一致（含空格和连字符），脚本里的 --action 直接查这个 dict。
action_map = {
    "release arm": 99,     # 释放/收回，保持型动作的收尾
    "two-hand kiss": 11,   # 双手飞吻
    "left kiss": 12,       # 左手飞吻
    "right kiss": 13,      # 右手飞吻
    "hands up": 15,        # 双手举起（保持型）
    "clap": 17,            # 拍手
    "high five": 18,       # 举手击掌（保持型）
    "hug": 19,             # 拥抱姿势（保持型）
    "heart": 20,           # 比心（保持型）
    "right heart": 21,     # 右手比心（保持型）
    "reject": 22,          # 拒绝手势
    "right hand up": 23,   # 举右手
    "x-ray": 24,           # 双手交叉成 X
    "face wave": 25,       # 脸旁挥手
    "high wave": 26,       # 高举挥手
    "shake hand": 27,      # 握手（保持型）
}


"""
" class SportClient
"""
class G1ArmActionClient(Client):
    def __init__(self):
        # 服务名 "arm" -> DDS topic rt/api/arm/request。
        super().__init__(ARM_ACTION_SERVICE_NAME, False)

    def Init(self):
        # set api version
        self._SetApiVerson(ARM_ACTION_API_VERSION)

        # regist api
        self._RegistApi(ROBOT_API_ID_ARM_ACTION_EXECUTE_ACTION, 0)
        self._RegistApi(ROBOT_API_ID_ARM_ACTION_GET_ACTION_LIST, 0)

    ## API Call ##
    def ExecuteAction(self, action_id: int):
        # ▶ 唯一的执行入口。参数就是 action_map 里的整数。
        #   返回 code：0 成功；7401 手臂正持有；7402 ID 非法；7404 FSM 不对。
        p = {}
        p["data"] = action_id
        parameter = json.dumps(p)
        code, data = self._Call(ROBOT_API_ID_ARM_ACTION_EXECUTE_ACTION, parameter)
        return code
    
    def GetActionList(self):
        # ▶ 问机器人"你支持哪些动作"。不同固件版本可能比 action_map 多或少。
        #   返回 (code, dict)；code != 0 时 dict 为 None。
        p = {}
        parameter = json.dumps(p)
        code, data = self._Call(ROBOT_API_ID_ARM_ACTION_GET_ACTION_LIST, parameter)
        if code == 0:
            return code, json.loads(data)
        else:
            return code, None
