// =============================================================================
// 课程阅读副本 · 官方 unitree_ros2 例程，逻辑未改动，只加了注释
// 上游: https://github.com/unitreerobotics/unitree_ros2
// 版本: 668d1ec5a05d1c38d3306bdca7d59f2ba3581a88（与 scripts/install.sh 固定的一致）
// 本文件: ros2_nodes/g1/g1_loco_client_example.cpp（上游原名 loco_client_example.cpp）
// 课程位置: 02_loco.py（FSM 与运控）
//
// ▶ 这是 LocoClient 的命令行例程：把 --key=value 解析成参数，按 key 调对应方法。
//   对照 02_loco.py 的 ACTIONS / OTHER_ACTIONS 两张表看，动作 ID 的完整含义在
//   g1_loco_client.hpp 的常量表与 FSM 总表里。
// ▶ include 路径按上游 example 工程的相对结构；若要自己编译，请把 ros2_nodes/g1
//   放回 example/src/src/g1 下。
//   仅阅读，不参与本仓库编译。
// =============================================================================

#include <chrono>
#include <g1/g1_loco_client.hpp>
#include <iostream>
#include <map>
#include <rclcpp/utilities.hpp>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

#include "common/ut_errror.hpp"
#include "rclcpp/rclcpp.hpp"

// ▶ 对应 02_loco.py 的 client = LocoClient()：这里把 LocoClient 包进一个 ROS 2 节点，
//   节点名 unitree_g1_control_node，后面所有运控指令都从这个节点发出去。
class UnitreeG1ControlNode : public rclcpp::Node {
 public:
  // ▶ 构造顺序对应 02_loco.py 的 LocoClient() + Init()；C++ 版把节点指针交给 client_。
  explicit UnitreeG1ControlNode(const std::map<std::string, std::string> &args)
      : Node("unitree_g1_control_node"), args_(args), client_(this) {
    // 起一个后台线程：先等 500 ms 让 DDS 和服务发现完成，再逐条执行命令行参数。
    // 02_loco.py 里对应的等待是 client.Init() 与 SetTimeout()。
    // Process commands
    thread_ = std::thread([this] {
      std::this_thread::sleep_for(std::chrono::milliseconds(500));
      ProcessCommands();
    });
  }
  // ▶ 对应 02_loco.py 的 explain(code)：0 表示成功，非 0 把错误码翻译成人话。
  bool handleActionError(int32_t error_code) {
    if (error_code == 0) {
      return true;
    }
    RCLCPP_ERROR(this->get_logger(), "Execute action failed, error code: %d",
                 error_code);
    // 7301 = LocoState 不可用：运控服务还没起来（先确认机器人已上电、网线接通）
    UT_PRINT_ERR(error_code,
                 unitree::robot::g1::UT_ROBOT_LOCO_ERR_LOCOSTATE_NOT_AVAILABLE);
    // 7302 = FSM ID 非法：这个机型不支持该状态，检查 set_fsm_id 给的数
    UT_PRINT_ERR(error_code,
                 unitree::robot::g1::UT_ROBOT_LOCO_ERR_INVALID_FSM_ID);
    // 7303 = Task ID 非法：挥手 / 握手的参数不对，只能是 0~3
    UT_PRINT_ERR(error_code,
                 unitree::robot::g1::UT_ROBOT_LOCO_ERR_INVALID_TASK_ID);
    // 公共超时码：请求发出去了，但机器人没在超时时间内回复
    UT_PRINT_ERR(error_code, UT_ROBOT_TASK_TIMEOUT);
    return false;
  }

 private:
  std::thread thread_;
  // ▶ 对应 02_loco.py 的 call_action()：按参数名分发到 LocoClient 的某个方法。
  //   命令格式是 --名字=值，例如 --set_fsm_id=500、--move=0.2 0 0。
  void ProcessCommands() {  // NOLINT
    for (const auto &arg_pair : args_) {
      RCLCPP_INFO(this->get_logger(),
                  "Processing command: [%s] with param: [%s]...",
                  arg_pair.first.c_str(), arg_pair.second.c_str());

      // ▶ 对应 02_loco.py 的 client.GetFsmId()；03_arm_actions.py 的 check_fsm() 也用它。api 7001。
      if (arg_pair.first == "get_fsm_id") {
        int fsm_id = 0;
        auto ret = client_.GetFsmId(fsm_id);
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "GetFsmId failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "current fsm_id: %d", fsm_id);
      }

      // ▶ 对应 Python 版 client.GetFsmMode()：读 FSM 子模式。api 7002。
      if (arg_pair.first == "get_fsm_mode") {
        int fsm_mode = 0;
        auto ret = client_.GetFsmMode(fsm_mode);
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "GetFsmMode failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "current fsm_mode: %d", fsm_mode);
      }

      // ▶ 对应 Python 版 client.GetBalanceMode()：0 平衡站立，1 连续步态。api 7003。
      if (arg_pair.first == "get_balance_mode") {
        int balance_mode = 0;
        auto ret = client_.GetBalanceMode(balance_mode);
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "GetBalanceMode failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "current balance_mode: %d",
                    balance_mode);
      }

      // ▶ 对应 Python 版 client.GetSwingHeight()：抬腿摆动高度，单位 m。api 7004。
      if (arg_pair.first == "get_swing_height") {
        float swing_height = NAN;
        auto ret = client_.GetSwingHeight(swing_height);
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "GetSwingHeight failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "current swing_height: %f",
                    swing_height);
      }

      // ▶ 对应 Python 版 client.GetStandHeight()：站立高度，单位 m。api 7005。
      if (arg_pair.first == "get_stand_height") {
        float stand_height = NAN;
        auto ret = client_.GetStandHeight(stand_height);
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "GetStandHeight failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "current stand_height: %f",
                    stand_height);
      }

      // ▶ 对应 Python 版 client.GetPhase()：步态相位（上游已标 deprecated）。api 7006。
      if (arg_pair.first == "get_phase") {
        std::vector<float> phase;
        auto ret = client_.GetPhase(phase);
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "GetPhase failed");
          continue;
        }
        std::stringstream ss;
        ss << "current phase: (";
        for (const auto &p : phase) {
          ss << p << ", ";
        }
        ss << ")";
        RCLCPP_INFO(this->get_logger(), "%s", ss.str().c_str());
      }

      // ▶ 对应 02_loco.py 的 client.SetFsmId(fsm)，也就是整个运控的核心。api 7101。
      //   FSM 取值：0=零力矩（会软倒） 1=阻尼 2=蹲下 3=坐下 4=站起
      //             500=进入主运控 706=蹲下/蹲起 702=仰躺站起。
      if (arg_pair.first == "set_fsm_id") {
        int fsm_id = std::stoi(arg_pair.second);
        auto ret = client_.SetFsmId(fsm_id);
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "SetFsmId failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "set fsm_id to %d", fsm_id);
      }

      // ▶ 对应 Python 版 client.SetBalanceMode(mode)：0 平衡站立，1 连续步态。api 7102。
      if (arg_pair.first == "set_balance_mode") {
        int balance_mode = std::stoi(arg_pair.second);
        auto ret = client_.SetBalanceMode(balance_mode);
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "SetBalanceMode failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "set balance_mode to %d", balance_mode);
      }

      // ▶ 对应 Python 版 client.SetSwingHeight(h)：设抬腿摆动高度，单位 m。api 7103。
      if (arg_pair.first == "set_swing_height") {
        float swing_height = std::stof(arg_pair.second);
        auto ret = client_.SetSwingHeight(swing_height);
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "SetSwingHeight failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "set swing_height to %f", swing_height);
      }

      // ▶ 对应 02_loco.py 的 high_stand / low_stand：0xFFFFFFFF 最高，0 最低。api 7104。
      if (arg_pair.first == "set_stand_height") {
        float stand_height = std::stof(arg_pair.second);
        auto ret = client_.SetStandHeight(stand_height);
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "SetStandHeight failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "set stand_height to %f", stand_height);
      }

      // ▶ 对应 Python 版 client.SetVelocity(vx, vy, omega, duration)：
      //   vx 前后、vy 左右、omega 转向；duration 单位秒。api 7105。
      if (arg_pair.first == "set_velocity") {
        std::vector<float> param = stringToFloatVector(arg_pair.second);
        auto param_size = param.size();
        float vx = NAN;
        float vy = NAN;
        float omega = NAN;
        float duration = NAN;
        if (param_size == 3) {
          vx = param.at(0);
          vy = param.at(1);
          omega = param.at(2);
          duration = 1.F;
        } else if (param_size == 4) {
          vx = param.at(0);
          vy = param.at(1);
          omega = param.at(2);
          duration = param.at(3);
        } else {
          RCLCPP_ERROR(this->get_logger(),
                       "Invalid param size for method SetVelocity: %zu",
                       param_size);
          continue;
        }

        auto ret = client_.SetVelocity(vx, vy, omega, duration);
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "SetVelocity failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "set velocity to %s",
                    arg_pair.second.c_str());
      }

      // ▶ 对应 02_loco.py 的 call_action("damp")：FSM 1 = 阻尼，关节变硬但不保持姿态。
      if (arg_pair.first == "damp") {
        auto ret = client_.Damp();
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "Damp failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "Damp command sent");
      }

      // ▶ 对应 02_loco.py 的 call_action("start")：FSM 500 = Start，
      //   进入“可被遥控 / 可运控”状态，必须先调它再走路或做手臂动作。
      if (arg_pair.first == "start") {
        auto ret = client_.Start();
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "Start failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "Start command sent");
      }

      // ▶ 对应 02_loco.py 的 call_action("squat")（脚本里写 SetFsmId(2)）：FSM 2 = 蹲下。
      if (arg_pair.first == "squat") {
        auto ret = client_.Squat();
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "Squat failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "Squat command sent");
      }

      // ▶ 对应 02_loco.py 的 call_action("sit")：FSM 3 = 坐下。
      if (arg_pair.first == "sit") {
        auto ret = client_.Sit();
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "Sit failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "Sit command sent");
      }

      // ▶ 对应 02_loco.py 的 call_action("stand_up")（脚本里写 SetFsmId(4)）：FSM 4 = 从坐/蹲站起。
      if (arg_pair.first == "stand_up") {
        auto ret = client_.StandUp();
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "StandUp failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "StandUp command sent");
      }

      // ▶ 对应 02_loco.py 的 call_action("zero_torque")：FSM 0 = 零力矩，
      //   关节立刻失去支撑，机器人会软倒（脚本要求加 --allow-dangerous）。
      if (arg_pair.first == "zero_torque") {
        auto ret = client_.ZeroTorque();
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "ZeroTorque failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "ZeroTorque command sent");
      }

      // ▶ 对应 02_loco.py 的 stop_move：SetVelocity(0,0,0)，只把速度清零，不退出 FSM。
      if (arg_pair.first == "stop_move") {
        auto ret = client_.StopMove();
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "StopMove failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "StopMove command sent");
      }

      // ▶ 对应 02_loco.py 的 high_stand：SetStandHeight(0xFFFFFFFF)，站到最高。
      if (arg_pair.first == "high_stand") {
        auto ret = client_.HighStand();
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "HighStand failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "HighStand command sent");
      }

      // ▶ 对应 02_loco.py 的 low_stand：SetStandHeight(0)，站到最低。
      if (arg_pair.first == "low_stand") {
        auto ret = client_.LowStand();
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "LowStand failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "LowStand command sent");
      }

      // ▶ 对应 02_loco.py 的 BalanceStand()：SetBalanceMode(0)，平衡站立。
      if (arg_pair.first == "balance_stand") {
        auto ret = client_.BalanceStand();
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "BalanceStand failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "BalanceStand command sent");
      }

      // ▶ 对应 Python 版 client.ContinuousGait(true/false)：
      //   true 走 SetBalanceMode(1) 连续步态，false 回 0 平衡站立。
      if (arg_pair.first == "continous_gait") {
        bool flag = false;
        if (arg_pair.second == "true") {
          flag = true;
        } else if (arg_pair.second == "false") {
          flag = false;
        } else {
          RCLCPP_ERROR(this->get_logger(), "invalid argument: %s",
                       arg_pair.second.c_str());
          continue;
        }
        auto ret = client_.ContinuousGait(flag);
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "ContinuousGait failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "ContinuousGait set to %s",
                    arg_pair.second.c_str());
      }

      // ▶ 对应 Python 版 client.SwitchMoveMode(true/false)：只改本地连续移动标志，不发请求。
      if (arg_pair.first == "switch_move_mode") {
        bool flag = false;
        if (arg_pair.second == "true") {
          flag = true;
        } else if (arg_pair.second == "false") {
          flag = false;
        } else {
          RCLCPP_ERROR(this->get_logger(), "invalid argument: %s",
                       arg_pair.second.c_str());
          continue;
        }
        auto ret = client_.SwitchMoveMode(flag);
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "SwitchMoveMode failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "SwitchMoveMode set to %s",
                    arg_pair.second.c_str());
      }

      // ▶ 对应 02_loco.py 的 move_forward / move_lateral / move_rotate：
      //   Move(vx, vy, omega)，底层还是 SetVelocity。
      if (arg_pair.first == "move") {
        std::vector<float> param = stringToFloatVector(arg_pair.second);
        auto param_size = param.size();
        float vx = NAN;
        float vy = NAN;
        float omega = NAN;
        if (param_size == 3) {
          vx = param.at(0);
          vy = param.at(1);
          omega = param.at(2);
        } else {
          RCLCPP_ERROR(this->get_logger(),
                       "Invalid param size for method SetVelocity: %zu",
                       param_size);
          continue;
        }
        auto ret = client_.Move(vx, vy, omega);
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "Move failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "Move command sent with params: %s",
                    arg_pair.second.c_str());
      }

      // ▶ 对应 02_loco.py 的 wave_hand / shake_hand：SetTaskId 的取值
      //   0=原地挥手 1=转身挥手 2=伸手准备握手 3=结束握手。api 7106。
      if (arg_pair.first == "set_task_id") {
        int task_id = std::stoi(arg_pair.second);
        auto ret = client_.SetTaskId(task_id);
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "SetTaskId failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "set task_id to %d", task_id);
      }

      // ▶ 对应 02_loco.py 的 shake_hand_start / shake_hand_end，分三步执行：
      if (arg_pair.first == "shake_hand") {
        // 第 1 步：ShakeHand(0) → SetTaskId(2)，伸手准备握手
        auto ret = client_.ShakeHand(0);
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "ShakeHand start failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(),
                    "Shake hand starts! Waiting for 10 s for ending");
        // 第 2 步：等 10 秒，让握手动作完整做完
        std::this_thread::sleep_for(std::chrono::seconds(10));
        // 第 3 步：ShakeHand(1) → SetTaskId(3)，结束握手、收回手臂
        auto ret_end = client_.ShakeHand(1);
        if (!handleActionError(ret_end)) {
          RCLCPP_ERROR(this->get_logger(), "ShakeHand end failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "Shake hand ends!");
      }

      // ▶ 对应 02_loco.py 的 wave_hand：SetTaskId(0)，原地挥手。
      if (arg_pair.first == "wave_hand") {
        auto ret = client_.WaveHand();
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "WaveHand failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "wave hand command sent");
      }

      // ▶ 对应 02_loco.py 的 wave_hand_turn：SetTaskId(1)，转身挥手。
      if (arg_pair.first == "wave_hand_with_turn") {
        auto ret = client_.WaveHand(true);
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "WaveHand with turn failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "wave hand with turn command sent");
      }

      // ▶ 对应 Python 版 client.SetSpeedMode(mode)：切换运控速度档位。api 7107。
      if (arg_pair.first == "set_speed_mode") {
        auto ret = client_.SetSpeedMode(std::stoi(arg_pair.second));
        if (!handleActionError(ret)) {
          RCLCPP_ERROR(this->get_logger(), "SetSpeedMode failed");
          continue;
        }
        RCLCPP_INFO(this->get_logger(), "set speed mode to %s",
                    arg_pair.second.c_str());
      }

      RCLCPP_INFO(this->get_logger(), "Done processing command: %s",
                  arg_pair.first.c_str());
    }
  }

  // ▶ 对应 02_loco.py 里把 "0.2 0.0 0.0" 拆成 vx/vy/vyaw 的那一步；
  //   这里用 stringstream 逐个读浮点数。
  static std::vector<float> stringToFloatVector(const std::string &str) {
    std::vector<float> result;
    std::stringstream ss(str);
    float num = NAN;
    while (ss >> num) {
      result.push_back(num);
      // ignore any trailing whitespace
      ss.ignore();
    }
    return result;
  }

  // 命令行参数表：key 是动作名，value 是它的参数（例如 move 的 "0.2 0 0"）。
  std::map<std::string, std::string> args_;
  // 真正干活的客户端；服务名在 g1_loco_client.hpp 里写死为 /api/sport/request。
  unitree::robot::g1::LocoClient client_;
};

// ▶ 对应 02_loco.py 的 main()：解析 --key=value，建节点，然后 spin 等后台线程执行。
int main(int argc, char const *argv[]) {
  rclcpp::init(argc, argv);

  std::map<std::string, std::string> args = {};

  // 解析 --key=value；没有 = 就当成空值（--damp 等价于 --damp=）。
  // Parse command line arguments
  for (int i = 1; i < argc; ++i) {
    std::string arg = argv[i];
    if (arg.substr(0, 2) == "--") {
      size_t pos = arg.find('=');
      std::string key;
      std::string value;
      if (pos != std::string::npos) {
        key = arg.substr(2, pos - 2);
        value = arg.substr(pos + 1);

        if (value.front() == '"' && value.back() == '"') {
          value = value.substr(1, value.length() - 2);
        }
      } else {
        key = arg.substr(2);
        value = "";
      }
      if (args.find(key) != args.end()) {
        args[key] = value;
      } else {
        args.insert({{key, value}});
      }
    }
  }
  // 一个参数都没有时只打印用法；用法里列的名字就是 ProcessCommands 里的分支名。
  if (args.size() == 0) {
    std::cout << "usage: g1_loco_client_example [--get_fsm_id | ...]"
              << std::endl;
    return 0;
  }
  auto node = std::make_shared<UnitreeG1ControlNode>(args);
  rclcpp::spin(node);
  rclcpp::shutdown();

  return 0;
}