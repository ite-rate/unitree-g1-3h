// =============================================================================
// 课程阅读副本 · 官方 unitree_ros2 例程，逻辑未改动，只加了注释
// 上游: https://github.com/unitreerobotics/unitree_ros2
// 版本: 668d1ec5a05d1c38d3306bdca7d59f2ba3581a88（与 scripts/install.sh 固定的一致）
// 本文件: ros2_nodes/g1/g1_loco_client.hpp
// 课程位置: 02_loco.py（FSM 与运控）
//
// ▶ 运控客户端的真实实现：所有动作最终都是「填 api_id + 拼 JSON 参数 + publish」。
//   02_loco.py 的 client.SetFsmId / SetVelocity / SetTaskId 对应这里的方法。
//   仅阅读，不参与本仓库编译。
// =============================================================================

#ifndef __UT_ROBOT_G1_LOCO_CLIENT_HPP__
#define __UT_ROBOT_G1_LOCO_CLIENT_HPP__

#include <cstdint>
#include <iostream>
#include <limits>
#include <rclcpp/node.hpp>
#include <string>

#include "base_client.hpp"
#include "common/ut_errror.hpp"
#include "detail/exceptions.hpp"
#include "nlohmann/json.hpp"
#include "patch.hpp"
#include "unitree_api/msg/request.hpp"
#include "unitree_api/msg/response.hpp"

// ▶ 查询类 api_id（7001–7006）：只读，不改变机器人状态。
// 7001 = GetFsmId：查当前 FSM 编号（现在处于哪个运控状态）
const int32_t ROBOT_API_ID_LOCO_GET_FSM_ID = 7001;
// 7002 = GetFsmMode：查 FSM 子模式
const int32_t ROBOT_API_ID_LOCO_GET_FSM_MODE = 7002;
// 7003 = GetBalanceMode：查平衡模式（0 平衡站立 / 1 连续步态）
const int32_t ROBOT_API_ID_LOCO_GET_BALANCE_MODE = 7003;
// 7004 = GetSwingHeight：查抬腿摆动高度，单位 m
const int32_t ROBOT_API_ID_LOCO_GET_SWING_HEIGHT = 7004;
// 7005 = GetStandHeight：查站立高度，单位 m
const int32_t ROBOT_API_ID_LOCO_GET_STAND_HEIGHT = 7005;
// 7006 = GetPhase：查步态相位（上游已废弃，仅为兼容保留）
const int32_t ROBOT_API_ID_LOCO_GET_PHASE = 7006;  // deprecated

// ▶ 设置类 api_id（7101–7107）：会改变机器人状态，02_loco.py 的每条指令最终都落到这里。
// 7101 = SetFsmId：切 FSM，站 / 蹲 / 坐 / 阻尼 / 进主运控全靠它
const int32_t ROBOT_API_ID_LOCO_SET_FSM_ID = 7101;
// 7102 = SetBalanceMode：0 平衡站立，1 连续步态
const int32_t ROBOT_API_ID_LOCO_SET_BALANCE_MODE = 7102;
// 7103 = SetSwingHeight：设抬腿摆动高度，单位 m
const int32_t ROBOT_API_ID_LOCO_SET_SWING_HEIGHT = 7103;
// 7104 = SetStandHeight：设站立高度，0xFFFFFFFF 最高 / 0 最低
const int32_t ROBOT_API_ID_LOCO_SET_STAND_HEIGHT = 7104;
// 7105 = SetVelocity：给速度 vx（前后）/ vy（左右）/ omega（转向），持续 duration 秒
const int32_t ROBOT_API_ID_LOCO_SET_VELOCITY = 7105;
// 7106 = SetArmTask：挥手 / 握手，0 原地挥、1 转身挥、2 伸手、3 结束握手；
//        和手臂服务的 7106 同号，但这里走 sport 服务，机器人按服务分派。
const int32_t ROBOT_API_ID_LOCO_SET_ARM_TASK = 7106;
// 7107 = SetSpeedMode：切换运控速度档位
const int32_t ROBOT_API_ID_LOCO_SET_SPEED_MODE = 7107;

namespace unitree::robot::g1 {

// 运控错误码：7301 运控状态不可用 / 7302 FSM ID 非法 / 7303 Task ID 非法。
UT_DECL_ERR(UT_ROBOT_LOCO_ERR_LOCOSTATE_NOT_AVAILABLE, 7301,
            "LocoState not available.")
UT_DECL_ERR(UT_ROBOT_LOCO_ERR_INVALID_FSM_ID, 7302, "Invalid fsm id.")
UT_DECL_ERR(UT_ROBOT_LOCO_ERR_INVALID_TASK_ID, 7303, "Invalid task id.")

// ▶ 对应 02_loco.py 的 client = LocoClient()：C++ 版不是独立进程，
//   需要先把一个 rclcpp::Node 传进来。
class LocoClient {
  // 借用的节点指针，只用来建客户端；节点本身归 main 里的 node 管理。
  rclcpp::Node* node_;
  // 底层请求/应答通道：服务名 "sport"，实际话题 /api/sport/request 与 /api/sport/response。
  BaseClient base_client_;

 public:
  // ▶ 对应 02_loco.py 的 client.Init()：构造时把两个话题名绑好。
  explicit LocoClient(rclcpp::Node* node)
      : node_(node),
        base_client_(node_, "/api/sport/request", "/api/sport/response") {}

  // 低层接口：直接填 api_id，参数用 nlohmann::json 拼，和 Python 版 json.dumps 一致。
  /*Low Level API Call*/
  // ▶ 对应 02_loco.py 的 client.GetFsmId()（api 7001）
  int32_t GetFsmId(int& fsm_id) {
    unitree_api::msg::Request req;
    req.header.identity.api_id = ROBOT_API_ID_LOCO_GET_FSM_ID;
    nlohmann::json js;
    int32_t ret = base_client_.Call(req, js);
    if (ret == 0) {
      js["data"].get_to(fsm_id);
    }

    return ret;
  }

  // ▶ 对应 Python 版 client.GetFsmMode()（api 7002）
  int32_t GetFsmMode(int& fsm_mode) {
    unitree_api::msg::Request req;
    req.header.identity.api_id = ROBOT_API_ID_LOCO_GET_FSM_MODE;
    nlohmann::json js;
    int32_t ret = base_client_.Call(req, js);
    if (ret == 0) {
      js["data"].get_to(fsm_mode);
    }

    return ret;
  }

  // ▶ 对应 Python 版 client.GetBalanceMode()（api 7003）
  int32_t GetBalanceMode(int& balance_mode) {
    unitree_api::msg::Request req;
    req.header.identity.api_id = ROBOT_API_ID_LOCO_GET_BALANCE_MODE;
    nlohmann::json js;
    int32_t ret = base_client_.Call(req, js);
    if (ret == 0) {
      js["data"].get_to(balance_mode);
    }

    return ret;
  }

  // ▶ 对应 Python 版 client.GetSwingHeight()（api 7004）
  int32_t GetSwingHeight(float& swing_height) {
    unitree_api::msg::Request req;
    req.header.identity.api_id = ROBOT_API_ID_LOCO_GET_SWING_HEIGHT;
    nlohmann::json js;
    int32_t ret = base_client_.Call(req, js);
    if (ret == 0) {
      std::cout << js.dump() << std::endl;
      js["data"].get_to(swing_height);
    } else {
      std::cerr << "Failed to connect to robot." << std::endl;
    }

    return ret;
  }

  // ▶ 对应 Python 版 client.GetStandHeight()（api 7005）
  int32_t GetStandHeight(float& stand_height) {
    unitree_api::msg::Request req;
    req.header.identity.api_id = ROBOT_API_ID_LOCO_GET_STAND_HEIGHT;
    nlohmann::json js;
    int32_t ret = base_client_.Call(req, js);
    if (ret == 0) {
      js["data"].get_to(stand_height);
    }

    return ret;
  }

  // ▶ 对应 Python 版 client.GetPhase()（api 7006，已废弃）
  int32_t GetPhase(std::vector<float>& phase) {
    unitree_api::msg::Request req;
    req.header.identity.api_id = ROBOT_API_ID_LOCO_GET_PHASE;
    nlohmann::json js;
    int32_t ret = base_client_.Call(req, js);
    if (ret == 0) {
      js["data"].get_to(phase);
    }

    return ret;
  }

  // ▶ 对应 02_loco.py 的 client.SetFsmId(fsm)（api 7101）。FSM 总表：
  //     0 = ZeroTorque   零力矩，关节失去支撑会软倒（危险）
  //     1 = Damp         阻尼，关节变硬但不保持姿态
  //     2 = Squat        蹲下
  //     3 = Sit          坐下
  //     4 = StandUp      从坐 / 蹲站起
  //   500 = Start        进入主运控，必须先调它再走路 / 做手臂动作
  //   702 = Lie2StandUp  仰躺站起（危险）
  //   706 = Squat2StandUp / StandUp2Squat，蹲起与蹲下共用
  int32_t SetFsmId(int fsm_id) {
    unitree_api::msg::Request req;
    req.header.identity.api_id = ROBOT_API_ID_LOCO_SET_FSM_ID;
    nlohmann::json js;
    js["data"] = fsm_id;
    req.parameter = js.dump();
    return base_client_.Call(req);
  }

  // ▶ client.SetBalanceMode(mode)：0 平衡站立，1 连续步态（api 7102）
  int32_t SetBalanceMode(int balance_mode) {
    unitree_api::msg::Request req;
    req.header.identity.api_id = ROBOT_API_ID_LOCO_SET_BALANCE_MODE;
    nlohmann::json js;
    js["data"] = balance_mode;
    req.parameter = js.dump();
    return base_client_.Call(req);
  }

  // ▶ client.SetSwingHeight(h)：抬腿摆动高度，单位 m（api 7103）
  int32_t SetSwingHeight(float swing_height) {
    unitree_api::msg::Request req;
    req.header.identity.api_id = ROBOT_API_ID_LOCO_SET_SWING_HEIGHT;
    nlohmann::json js;
    js["data"] = swing_height;
    req.parameter = js.dump();
    return base_client_.Call(req);
  }

  // ▶ 02_loco.py 的 high_stand / low_stand 走这里：0xFFFFFFFF 最高，0 最低（api 7104）
  int32_t SetStandHeight(float stand_height) {
    unitree_api::msg::Request req;
    req.header.identity.api_id = ROBOT_API_ID_LOCO_SET_STAND_HEIGHT;
    nlohmann::json js;
    js["data"] = stand_height;
    req.parameter = js.dump();
    return base_client_.Call(req);
  }

  // ▶ move_forward / move_lateral / move_rotate 走这里：
  //   vx 前后、vy 左右、omega 转向，duration 单位秒（api 7105）
  int32_t SetVelocity(float vx, float vy, float omega, float duration = 1.F) {
    unitree_api::msg::Request req;
    req.header.identity.api_id = ROBOT_API_ID_LOCO_SET_VELOCITY;
    nlohmann::json js;
    std::vector<float> velocity = {vx, vy, omega};
    js["velocity"] = velocity;
    js["duration"] = duration;
    req.parameter = js.dump();
    return base_client_.Call(req);
  }

  // ▶ wave_hand / shake_hand 走这里：0 原地挥手、1 转身挥手、2 伸手、3 结束握手（api 7106）
  int32_t SetTaskId(int task_id) {
    unitree_api::msg::Request req;
    req.header.identity.api_id = ROBOT_API_ID_LOCO_SET_ARM_TASK;
    nlohmann::json js;
    js["data"] = task_id;
    req.parameter = js.dump();
    return base_client_.Call(req);
  }

  // ▶ client.SetSpeedMode(mode)：运控速度档位（api 7107）
  int32_t SetSpeedMode(int speed_mode) {
    unitree_api::msg::Request req;
    req.header.identity.api_id = ROBOT_API_ID_LOCO_SET_SPEED_MODE;
    nlohmann::json js;
    js["data"] = speed_mode;
    req.parameter = js.dump();
    return base_client_.Call(req);
  }

  // 高层封装：只是 SetFsmId / SetBalanceMode / SetTaskId 的语法糖；
  // 02_loco.py 为了拿到返回码，多数直接调低层的 SetFsmId。
  /*High Level API Call*/
  // ▶ 对应 02_loco.py 的 call_action("damp")：FSM 1
  int32_t Damp() { return SetFsmId(1); }

  // ▶ 对应 02_loco.py 的 call_action("start")：FSM 500，进入主运控
  int32_t Start() { return SetFsmId(500); }

  // ▶ 对应 02_loco.py 的 call_action("squat")：FSM 2，蹲下
  int32_t Squat() { return SetFsmId(2); }

  // ▶ 对应 02_loco.py 的 call_action("sit")：FSM 3，坐下
  int32_t Sit() { return SetFsmId(3); }

  // ▶ 对应 02_loco.py 的 call_action("stand_up")：FSM 4，从坐 / 蹲站起
  int32_t StandUp() { return SetFsmId(4); }

  // ▶ 对应 02_loco.py 的 call_action("zero_torque")：FSM 0，机器人会软倒（危险）
  int32_t ZeroTorque() { return SetFsmId(0); }

  // ▶ 对应 02_loco.py 的 stop_move：SetVelocity(0,0,0)，只停速度不退出 FSM
  int32_t StopMove() { return SetVelocity(0.F, 0.F, 0.F); }

  // ▶ 对应 02_loco.py 的 high_stand：站到最高
  int32_t HighStand() {
    return SetStandHeight(
        static_cast<float>(std::numeric_limits<uint32_t>::max()));
  }

  // ▶ 对应 02_loco.py 的 low_stand：站到最低
  int32_t LowStand() {
    return SetStandHeight(std::numeric_limits<uint32_t>::min());
  }

  // ▶ 对应 02_loco.py 的 move_forward 等：continous_move=true 时
  //   duration 给 864000 秒（等于一直走），false 时只走 1 秒。
  int32_t Move(float vx, float vy, float vyaw, bool continous_move) {
    return SetVelocity(vx, vy, vyaw, continous_move ? 864000.F : 1.F);
  }

  // ▶ 不带 bool 的重载：沿用 SwitchMoveMode 存下的 continous_move_。
  int32_t Move(float vx, float vy, float vyaw) {
    return Move(vx, vy, vyaw, continous_move_);
  }

  // ▶ client.BalanceStand()：SetBalanceMode(0)
  int32_t BalanceStand() { return SetBalanceMode(0); }

  // ▶ client.ContinuousGait(true/false)：SetBalanceMode(1/0)
  int32_t ContinuousGait(bool flag) { return SetBalanceMode(flag ? 1 : 0); }

  // ▶ client.SwitchMoveMode(true/false)：只改本地标志，不发请求
  int32_t SwitchMoveMode(bool flag) {
    continous_move_ = flag;
    return 0;
  }

  // ▶ 对应 02_loco.py 的 wave_hand / wave_hand_turn：SetTaskId(0/1)
  int32_t WaveHand(bool turn_flag = false) {
    return SetTaskId(turn_flag ? 1 : 0);
  }

  // ▶ 对应 02_loco.py 的 shake_hand_start(2) / shake_hand_end(3)；
  //   stage 不填时在 2 / 3 之间来回切。
  int32_t ShakeHand(int stage = -1) {
    switch (stage) {
      case 0:
        first_shake_hand_stage_ = false;
        return SetTaskId(2);

      case 1:
        first_shake_hand_stage_ = true;
        return SetTaskId(3);

      default:
        first_shake_hand_stage_ = !first_shake_hand_stage_;
        return SetTaskId(first_shake_hand_stage_ ? 3 : 2);
    }
  }

 private:
  // continous_move_：连续移动开关，由 SwitchMoveMode 改。
  // first_shake_hand_stage_：下一次握手该发 2 还是 3。
  bool continous_move_ = false;
  bool first_shake_hand_stage_ = true;
};
}  // namespace unitree::robot::g1

#endif  // __UT_ROBOT_G1_LOCO_CLIENT_HPP__