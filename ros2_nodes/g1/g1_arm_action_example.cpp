// =============================================================================
// 课程阅读副本 · 官方 unitree_ros2 例程，逻辑未改动，只加了注释
// 上游: https://github.com/unitreerobotics/unitree_ros2
// 版本: 668d1ec5a05d1c38d3306bdca7d59f2ba3581a88（与 scripts/install.sh 固定的一致）
// 本文件: ros2_nodes/g1/g1_arm_action_example.cpp
// 课程位置: 03_arm_actions.py（手臂动作）
//
// ▶ 手臂动作例程：键盘输入 action_id，调 G1ArmActionClient::ExecuteAction 执行。
//   16 个 action_id 的对照表在 ProcessAction 上方。
// ▶ include 路径按上游 example 工程的相对结构；若要自己编译，请把 ros2_nodes/g1
//   放回 example/src/src/g1 下。
//   仅阅读，不参与本仓库编译。
// =============================================================================

/**
 * @file g1_arm_action_example.cpp
 * @brief This example demonstrates how to use the G1 Arm Action Client to
 * execute predefined arm actions in ROS2.
 */
#include <iostream>
#include <memory>
#include <string>
#include <thread>

#include "common/ut_errror.hpp"
#include "g1/g1_arm_action_client.hpp"
#include "rclcpp/rclcpp.hpp"

// ▶ 对应 03_arm_actions.py：交互式输入一个 action_id，然后 arm.ExecuteAction(id)。
class G1ArmActionNode : public rclcpp::Node {
 public:
  // ▶ 对应 03_arm_actions.py 的 arm.Init()：节点名 g1_arm_action_node，
  //   客户端服务名在 g1_arm_action_client.hpp 里是 "arm"。
  explicit G1ArmActionNode() : Node("g1_arm_action_node") {
    client_ = std::make_shared<unitree::robot::g1::G1ArmActionClient>(this);

    // 后台线程每 100 ms 查一次键盘，对应 03_arm_actions.py 的 input() 循环。
    thread_ = std::thread([this] {
      using namespace std::chrono_literals;
      while (true) {
        std::this_thread::sleep_for(100ms);
        checkForInput();
      }
    });
  }

 private:
  // ▶ 对应 03_arm_actions.py 的 print_list()：第一次进来先把用法和注意事项打出来。
  void checkForInput() {
    static std::string line;
    static bool getting_input = false;
    // 输入 0 = 打印固件支持的动作列表（走 GetActionList，api 7107）；
    // 输入数字 = 执行对应动作（走 ExecuteAction，api 7106）。
    RCLCPP_INFO(this->get_logger(),
                "G1 Arm Action Node initialized\n"
                "Usage:\n"
                "  - 0: print supported actions.\n"
                "  - an id: execute an action.\n"
                "Attention:\n"
                "  Some actions will not be displayed on the APP,\n"
                "  but can be executed by the program.\n"
                "  These actions may cause the robot to fall,\n"
                "  so please execute them with caution.");
    if (!getting_input) {
      std::cout << "\nEnter action ID (or 'q' to quit): ";
      getting_input = true;
    }

    if (std::cin.peek() != EOF) {
      std::getline(std::cin, line);
      getting_input = false;

      // 输入 q 退出，等价于 03_arm_actions.py 里按 Ctrl+C。
      if (line == "q") {
        rclcpp::shutdown();
        return;
      }

      try {
        int32_t action_id = std::stoi(line);
        ProcessAction(action_id);
      } catch (const std::exception& e) {
        RCLCPP_ERROR(this->get_logger(),
                     "Invalid input: %s. Please enter an integer.", e.what());
      }
    }
  }

  // ▶ 对应 03_arm_actions.py 的主循环：id=0 查列表，其余 ExecuteAction(id)。
  //   手臂动作只在 FSM 500 / 501 / 801 下可用，否则报 7404。
  //   固件预置的 action_id（03_arm_actions.py 的 ARMS 表）：
  //     99 = release arm    释放 / 收回手臂，保持型动作的收尾
  //     11 = two-hand kiss  双手飞吻
  //     12 = left kiss      左手飞吻
  //     13 = right kiss     右手飞吻
  //     15 = hands up       双手举起（保持型，重心会变）
  //     17 = clap           拍手
  //     18 = high five      举手击掌（保持型）
  //     19 = hug            拥抱姿势（保持型）
  //     20 = heart          比心（保持型）
  //     21 = right heart    右手比心（保持型）
  //     22 = reject         拒绝手势
  //     23 = right hand up  举右手
  //     24 = x-ray          双手交叉成 X
  //     25 = face wave      脸旁挥手
  //     26 = high wave      高举挥手
  //     27 = shake hand     握手（保持型）
  void ProcessAction(int32_t action_id) {
    // action_id = 0 是“打印列表”的约定，走 api 7107，不执行动作。
    if (action_id == 0) {
      std::string action_list_data;
      int32_t ret = client_->GetActionList(action_list_data);
      if (ret != 0) {
        handleActionError(ret);
        return;
      }
      RCLCPP_INFO(this->get_logger(), "Available actions:\n%s",
                  action_list_data.c_str());
    } else {
      // 其余 id 走 api 7106，机器人按固件里编好的轨迹做动作。
      int32_t ret = client_->ExecuteAction(action_id);
      if (ret != 0) {
        handleActionError(ret);
      } else {
        RCLCPP_INFO(this->get_logger(), "Action %d executed successfully",
                    action_id);
      }
    }
  }

  // ▶ 对应 03_arm_actions.py 的 explain(code) 与 ARM_ERRORS 表。
  void handleActionError(int32_t error_code) {
    RCLCPP_ERROR(this->get_logger(), "Execute action failed, error code: %d",
                 error_code);
    // 7400 = rt/armsdk 被占用：别的进程正在控手臂，先关掉它
    UT_PRINT_ERR(error_code,
                 unitree::robot::g1::UT_ROBOT_ARM_ACTION_ERR_ARMSDK);
    // 7401 = 手臂正持有上一个动作：先发 99 release arm，或重复同一动作
    UT_PRINT_ERR(error_code,
                 unitree::robot::g1::UT_ROBOT_ARM_ACTION_ERR_HOLDING);
    // 7402 = action_id 非法：对照上面 ProcessAction 里的动作表
    UT_PRINT_ERR(error_code,
                 unitree::robot::g1::UT_ROBOT_ARM_ACTION_ERR_INVALID_ACTION_ID);
    // 7404 = 当前 FSM 不支持手臂动作：先跑 02_loco.py --action start
    UT_PRINT_ERR(error_code,
                 unitree::robot::g1::UT_ROBOT_ARM_ACTION_ERR_INVALID_FSM_ID);
    // 公共超时码：机器人没在规定时间内回复
    UT_PRINT_ERR(error_code, UT_ROBOT_TASK_TIMEOUT);
  }

  // 轮询键盘的后台线程。
  std::thread thread_;
  // 手臂动作客户端，内部服务名 "arm"，话题 /api/arm/request。
  std::shared_ptr<unitree::robot::g1::G1ArmActionClient> client_;
};

// ▶ 对应 03_arm_actions.py 的 main()：初始化 ROS 2，建节点，spin。
int main(int argc, const char** argv) {
  rclcpp::init(argc, argv);

  auto node = std::make_shared<G1ArmActionNode>();
  rclcpp::spin(node);
  rclcpp::shutdown();

  return 0;
}