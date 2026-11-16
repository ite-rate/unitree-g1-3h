// =============================================================================
// 课程阅读副本 · 官方 unitree_ros2 例程，逻辑未改动，只加了注释
// 上游: https://github.com/unitreerobotics/unitree_ros2
// 版本: 668d1ec5a05d1c38d3306bdca7d59f2ba3581a88（与 scripts/install.sh 固定的一致）
// 本文件: ros2_nodes/g1/g1_arm_action_client.hpp
// 课程位置: 03_arm_actions.py（手臂动作）
//
// ▶ 手臂动作客户端：服务名 "arm"，只发一个 action_id（api 7106）。
//   action_id 的完整对照表在 g1_arm_action_example.cpp 的 ProcessAction 上方。
//   仅阅读，不参与本仓库编译。
// =============================================================================

#pragma once

#include <cstdint>
#include <future>
#include <map>
#include <memory>
#include <rclcpp/node.hpp>
#include <rclcpp/qos.hpp>
#include <string>

#include "base_client.hpp"
#include "common/ut_errror.hpp"
#include "nlohmann/json.hpp"
#include "patch.hpp"
#include "unitree_api/msg/request.hpp"
#include "unitree_api/msg/response.hpp"

#define UT_DECL_ERR(name, code, desc) \
  const int32_t name = code;          \
  const constexpr char* name##_DESC = desc;

namespace unitree::robot::g1 {

// 错误码：7400 手臂服务被占用 / 7401 手臂正持有动作 /
//         7402 action_id 非法 / 7404 当前 FSM 不支持。
UT_DECL_ERR(UT_ROBOT_ARM_ACTION_ERR_ARMSDK, 7400,
            "The topic rt/armsdk is occupied.")
UT_DECL_ERR(UT_ROBOT_ARM_ACTION_ERR_HOLDING, 7401,
            "The arm is holding. Expecting release action(99) or the same last "
            "action id.")
UT_DECL_ERR(UT_ROBOT_ARM_ACTION_ERR_INVALID_ACTION_ID, 7402,
            "Invalid action id.")
// The actions are only supported in fsm id {500, 501, 801};
// You can subscribe the topic rt/sportmodestate to check the fsm id.
// And in the state 801, the actions are only supported in the fsm mode {0, 3}.
// See
// https://support.unitree.com/home/en/G1_developer/sport_services_interface#Expert%20interface
UT_DECL_ERR(
    UT_ROBOT_ARM_ACTION_ERR_INVALID_FSM_ID, 7404,
    "Invalid fsm id.\n"
    "The actions are only supported in fsm id {500, 501, 801}.\n"
    "You can subscribe the topic rt/sportmodestate to check the fsm id.\n"
    "And in the state 801, the actions are only supported in the fsm "
    "mode {0, 3}.\n"
    "See "
    "https://support.unitree.com/home/en/G1_developer/"
    "sport_services_interface#Expert%20interface");

// 7106 = ExecuteAction：发一个 action_id，让固件执行预置手臂动作（99 / 11 / 12 / … / 27）
const int32_t ROBOT_API_ID_ARM_ACTION_EXECUTE_ACTION = 7106;
// 7107 = GetActionList：读固件支持的动作列表（例程里输入 0 时用它）
// 注意：7106 / 7107 和运控服务的 SetTaskId / SetSpeedMode 同号，但服务不同——
// 这里走 "arm" 服务，那边走 "sport" 服务，机器人按服务分派，不会冲突。
const int32_t ROBOT_API_ID_ARM_ACTION_GET_ACTION_LIST = 7107;

// ▶ 对应 03_arm_actions.py 的 arm = G1ArmActionClient()。
class G1ArmActionClient {
  // 借用外部节点指针，节点归调用方管理。
  rclcpp::Node* node_;
  // 服务名 "arm"：话题 /api/arm/request 与 /api/arm/response。
  BaseClient base_client_;

 public:
  // ▶ 对应 03_arm_actions.py 的 arm.Init()：构造时把两个话题名绑好。
  explicit G1ArmActionClient(rclcpp::Node* node)
      : node_(node),
        base_client_(node_, "/api/arm/request", "/api/arm/response") {}

  // ▶ 对应 03_arm_actions.py 的 arm.ExecuteAction(action_id)（api 7106）。
  int32_t ExecuteAction(int32_t action_id) {
    unitree_api::msg::Request req;
    req.header.identity.api_id = ROBOT_API_ID_ARM_ACTION_EXECUTE_ACTION;
    nlohmann::json js;
    js["data"] = action_id;
    req.parameter = js.dump();
    return base_client_.Call(req);
  }

  // ▶ 对应 03_arm_actions.py --list / 输入 0：读固件支持的动作列表（api 7107）。
  int32_t GetActionList(std::string& data) {
    unitree_api::msg::Request req;
    req.header.identity.api_id = ROBOT_API_ID_ARM_ACTION_GET_ACTION_LIST;

    nlohmann::json js_res;
    auto result = base_client_.Call(req, js_res);
    if (result == 0) {
      data = js_res.dump();
    }
    return result;
  }
};

}  // namespace unitree::robot::g1
