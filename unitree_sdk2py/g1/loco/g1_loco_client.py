# =============================================================================
# 课程阅读副本 · 官方源码，逻辑未改动，只加了注释
# 上游: unitree_sdk2_python（unitree-robotics/unitree_sdk2_python）
# 版本: 814556d15970dd2ecf1c9984e845ca02ab07e206
# 本文件: unitree_sdk2py/g1/loco/g1_loco_client.py
# 课程位置: 02_loco.py
#
# ▶ G1 运控客户端。所有方法最终都走 RPC：
#       你的进程 --(DDS topic rt/api/sport/request)--> 机器人运控服务
#   返回值 code=0 表示机器人接受了请求；非 0 见 g1_loco_api.py 末尾的错误码表。
#
# ▶ 本文件最容易踩的两个坑：
#   1. Damp()/Start()/Sit() 这些"语法糖"都不 return，`code = client.Damp()`
#      拿到的是 None。要拿返回码就自己调 client.SetFsmId(x)。
#   2. Python 版没有 Squat()/StandUp()（C++ 版有），用 SetFsmId(2)/(4)。
# =============================================================================
import json

from ...rpc.client import Client
from .g1_loco_api import *

"""
" class SportClient
"""
class LocoClient(Client):
    def __init__(self):
        # 第二个参数 False = 不启用租约（lease）。G1 的 sport 服务不需要租约。
        super().__init__(LOCO_SERVICE_NAME, False)
        # 握手状态在客户端本地记：-1 表示还没握过，True/False 表示上一阶段。
        self.first_shake_hand_stage_ = -1

    def Init(self):
        # set api version
        self._SetApiVerson(LOCO_API_VERSION)

        # regist api
        # ▶ 注册 = 告诉 RPC 客户端"我要用这些 API"，第二个参数 0 表示无租约。
        #   不注册就 _Call，会直接报"api not registered"。
        self._RegistApi(ROBOT_API_ID_LOCO_GET_FSM_ID, 0)
        self._RegistApi(ROBOT_API_ID_LOCO_GET_FSM_MODE, 0)
        self._RegistApi(ROBOT_API_ID_LOCO_GET_BALANCE_MODE, 0)
        self._RegistApi(ROBOT_API_ID_LOCO_GET_SWING_HEIGHT, 0)
        self._RegistApi(ROBOT_API_ID_LOCO_GET_STAND_HEIGHT, 0)
        self._RegistApi(ROBOT_API_ID_LOCO_GET_PHASE, 0) # deprecated

        self._RegistApi(ROBOT_API_ID_LOCO_SET_FSM_ID, 0)
        self._RegistApi(ROBOT_API_ID_LOCO_SET_BALANCE_MODE, 0)
        self._RegistApi(ROBOT_API_ID_LOCO_SET_SWING_HEIGHT, 0)
        self._RegistApi(ROBOT_API_ID_LOCO_SET_STAND_HEIGHT, 0)
        self._RegistApi(ROBOT_API_ID_LOCO_SET_VELOCITY, 0)
        self._RegistApi(ROBOT_API_ID_LOCO_SET_ARM_TASK, 0)
        self._RegistApi(ROBOT_API_ID_LOCO_SET_SPEED_MODE, 0)
        self._RegistApi(ROBOT_API_ID_LOCO_SWITCH_TO_USER_CTRL, 0)
        self._RegistApi(ROBOT_API_ID_LOCO_SWITCH_TO_INTERNAL_CTRL, 0)

    # 7001
    def GetFsmId(self):
        # ▶ 返回 (code, fsm_id)。fsm_id 是数字，含义见 g1_loco_api.py 的 FSM 表。
        #   手臂动作前用它检查是不是 500/501/801。
        p = {}
        parameter = json.dumps(p)
        code, data = self._Call(ROBOT_API_ID_LOCO_GET_FSM_ID, parameter)
        if code != 0:
            return code, None
        js = json.loads(data)
        return code, js.get("data")

    # 7101
    def SetFsmId(self, fsm_id: int):
        # ▶ 最核心的方法：切状态机。
        #   1  阻尼       2  蹲       3  坐       4  站起
        #   500 进入主运控  702 躺姿站起  706 蹲姿站起
        #   0  零力矩（会软倒，危险）
        p = {}
        p["data"] = fsm_id
        parameter = json.dumps(p)
        code, data = self._Call(ROBOT_API_ID_LOCO_SET_FSM_ID, parameter)
        return code

    # 7102
    def SetBalanceMode(self, balance_mode: int):
        # ▶ 平衡模式，具体编号由固件定义；课堂不展开。
        p = {}
        p["data"] = balance_mode
        parameter = json.dumps(p)
        code, data = self._Call(ROBOT_API_ID_LOCO_SET_BALANCE_MODE, parameter)
        return code

    # 7104
    def SetStandHeight(self, stand_height: float):
        # ▶ 站立高度。0 = 最低，0xFFFFFFFF = 最高（HighStand 就是这么发的）。
        p = {}
        p["data"] = stand_height
        parameter = json.dumps(p)
        code, data = self._Call(ROBOT_API_ID_LOCO_SET_STAND_HEIGHT, parameter)
        return code

    # 7105
    def SetVelocity(self, vx: float, vy: float, omega: float, duration: float = 1.0):
        # ▶ 在运控里给速度：[前后 vx, 左右 vy, 转向 omega]，duration 秒后自动停。
        #   vx 正 = 前进；vy 正 = 左移；omega 正 = 逆时针。
        #   想让机器人一直走，就传一个很大的 duration（见 Move 的 864000）。
        p = {}
        velocity = [vx,vy,omega]
        p["velocity"] = velocity
        p["duration"] = duration
        parameter = json.dumps(p)
        code, data = self._Call(ROBOT_API_ID_LOCO_SET_VELOCITY, parameter)
        return code
    
    # 7106
    def SetTaskId(self, task_id: float):
        # ▶ 任务 ID：0 原地挥手，1 转身挥手，2 开始握手，3 结束握手。
        #   注意它和手臂动作（G1ArmActionClient，7106 但服务名是 "arm"）不是一回事：
        #   这里是 sport 服务，只做挥手/握手。
        p = {}
        p["data"] = task_id
        parameter = json.dumps(p)
        code, data = self._Call(ROBOT_API_ID_LOCO_SET_ARM_TASK, parameter)
        return code

    # 7107
    def SetSpeedMode(self, speed_mode: int):
        # ▶ 速度档位，编号由固件定义；课堂不展开。
        p = {}
        p["data"] = speed_mode
        parameter = json.dumps(p)
        code, data = self._Call(ROBOT_API_ID_LOCO_SET_SPEED_MODE, parameter)
        return code

    # 7110
    def SwitchToUserCtrl(self):
        # ▶ 把控制权交给用户程序。上游这里固定发 False，实际用途以固件为准。
        p = {}
        p["data"] = False
        parameter = json.dumps(p)
        code, data = self._Call(ROBOT_API_ID_LOCO_SWITCH_TO_USER_CTRL, parameter)
        return code

    # 7111
    def SwitchToInternalCtrl(self, mode: InternalFsmMode):
        # ▶ 把控制权还给内部运控。mode 见 InternalFsmMode（LAST/PASSIVE/WALKRUN）。
        p = {}
        if mode == InternalFsmMode.LAST:
            p["data"] = 0
        elif mode == InternalFsmMode.PASSIVE:
            p["data"] = 1
        elif mode == InternalFsmMode.WALKRUN:
            p["data"] = 2
        else:
            raise ValueError(f"Invalid InternalFsmMode: {mode}")
        parameter = json.dumps(p)
        code, data = self._Call(ROBOT_API_ID_LOCO_SWITCH_TO_INTERNAL_CTRL, parameter)
        return code

    # ▶ 以下都是语法糖。注意：全部没有 return，所以返回 None。
    #   要判断成功失败，请直接调用上面对应的 SetXxx()。
    def Damp(self):
        # 阻尼保护（FSM 1）。课程里最常用的"先让机器人安全下来"。
        self.SetFsmId(1)
    
    def Start(self):
        # 进入主运控（FSM 500）。手臂动作之前必须先到这里。
        self.SetFsmId(500)

    def Squat2StandUp(self):
        # 从蹲姿站起（FSM 706）。现场最常用的"站起来"。
        self.SetFsmId(706)

    def Lie2StandUp(self):
        # 从仰躺站起（FSM 702）。要求机器人仰面、地面硬且平，危险。
        self.SetFsmId(702)

    def Sit(self):
        # 坐下（FSM 3）。
        self.SetFsmId(3)

    def StandUp2Squat(self):
        # ▶ 上游这里也写 706，和 Squat2StandUp 完全一样。
        #   按 C++ 版语义它是"蹲下"，但 Python 版权威动作以 2（squat）为准。
        self.SetFsmId(706)

    def ZeroTorque(self):
        # ▶ 零力矩（FSM 0）：关节立刻不发力，机器人会软倒。危险动作。
        self.SetFsmId(0)

    def StopMove(self):
        # 速度清零。注意它也没有 return。
        self.SetVelocity(0., 0., 0.)

    def HighStand(self):
        # 站到最高：高度设成 uint32 最大值，固件会解释为"最高"。
        UINT32_MAX = (1 << 32) - 1
        self.SetStandHeight(UINT32_MAX)

    def LowStand(self):
        # 站到最低：高度设 0。
        UINT32_MIN = 0
        self.SetStandHeight(UINT32_MIN)

    def Move(self, vx: float, vy: float, vyaw: float, continous_move: bool = False):
        # ▶ continous_move=True 时 duration=864000 秒（10 天），等于"一直走"，
        #   必须自己再调 StopMove/SetVelocity(0,0,0)。
        #   默认 False = 只走 1 秒。注意上游把 continuous 拼成了 continous。
        duration = 864000.0 if continous_move else 1
        self.SetVelocity(vx, vy, vyaw, duration)

    def BalanceStand(self, balance_mode: int):
        # ▶ Python 版要求传 balance_mode；C++ 版有无参重载。
        self.SetBalanceMode(balance_mode)

    def WaveHand(self, turn_flag: bool = False):
        # ▶ turn_flag=False -> Task 0 原地挥手；True -> Task 1 转身挥手。
        self.SetTaskId(1 if turn_flag else 0)

    def ShakeHand(self, stage: int = -1):
        # ▶ stage=0 开始握手（Task 2）；stage=1 结束（Task 3）；
        #   stage=-1 自动在 2/3 之间来回切（第一次从 -1 变成 True -> 发 3）。
        if stage == 0:
            self.first_shake_hand_stage_ = False
            self.SetTaskId(2)
        elif stage == 1:
            self.first_shake_hand_stage_ = True
            self.SetTaskId(3)
        else:
            self.first_shake_hand_stage_ = not self.first_shake_hand_stage_
            return self.SetTaskId(3 if self.first_shake_hand_stage_ else 2)
    
