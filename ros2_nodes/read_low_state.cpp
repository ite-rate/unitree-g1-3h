// =============================================================================
// 课程阅读副本 · 官方 unitree_ros2 例程，逻辑未改动，只加了注释
// 上游: https://github.com/unitreerobotics/unitree_ros2
// 版本: 668d1ec5a05d1c38d3306bdca7d59f2ba3581a88（与 scripts/install.sh 固定的一致）
// 本文件: ros2_nodes/read_low_state.cpp
// 课程位置: 01_ros2_subscriber.py（对照 C++ 写法）
//
// ▶ ROS 2 节点最小骨架，和 01_ros2_subscriber.py 是同一件事：
//     class LowStateSuber : public rclcpp::Node
//     create_subscription<unitree_go::msg::LowState>("lowstate", 10, callback)
//     rclcpp::spin(...)
//
//   ▶ 为什么 topic 名是 "lowstate"，而 SDK 里写 "rt/lowstate"？
//     ROS 2 会在名字前加 "rt/"，所以 ROS 2 的 /lowstate 就是 DDS 的 rt/lowstate。
//     两边看到的是同一股数据，不需要桥接节点。
//
//   ▶ 这个例程只打印，不发控制指令；打印很重，所以别拿它当高频采集工具。
//   仅阅读，不参与本仓库编译（完整编译见 unitree_ros2 官方仓库）。
// =============================================================================
/**
 * This example demonstrates how to use ROS2 to receive low states of unitree
 *go2 robot
 **/
#include "rclcpp/rclcpp.hpp"
#include "unitree_go/msg/imu_state.hpp"
#include "unitree_go/msg/low_state.hpp"
#include "unitree_go/msg/motor_state.hpp"

constexpr bool INFO_IMU = true;         // Set 1 to info IMU states
constexpr bool INFO_MOTOR = true;       // Set 1 to info motor states
constexpr bool INFO_FOOT_FORCE = true;  // Set 1 to info foot force states
constexpr bool INFO_BATTERY = true;     // Set 1 to info battery states
constexpr bool HIGH_FREQ = true;
// Set 1 to subscribe to low states with high frequencies (500Hz)

class LowStateSuber : public rclcpp::Node {
 public:
  LowStateSuber() : Node("low_state_suber") {
    // suber is set to subscribe "/lowcmd" or  "lf/lowstate" (low frequencies)
    // topic
    const auto *topic_name = "hf/lowstate";
    if (HIGH_FREQ) {
      topic_name = "lowstate";
    }
    // The suber  callback function is bind to low_state_suber::topic_callback
    suber_ = this->create_subscription<unitree_go::msg::LowState>(
        topic_name, 10,
        [this](const unitree_go::msg::LowState::SharedPtr data) {
          topic_callback(data);
        });
  }

 private:
  void topic_callback(const unitree_go::msg::LowState::SharedPtr &data) {
    if (INFO_IMU) {
      // Info IMU states
      // RPY euler angle(ZYX order respected to body frame)
      // Quaternion
      // Gyroscope (raw data)
      // Accelerometer (raw data)
      imu_ = data->imu_state;

      RCLCPP_INFO(this->get_logger(),
                  "Euler angle -- roll: %f; pitch: %f; yaw: %f", imu_.rpy[0],
                  imu_.rpy[1], imu_.rpy[2]);
      RCLCPP_INFO(this->get_logger(),
                  "Quaternion -- qw: %f; qx: %f; qy: %f; qz: %f",
                  imu_.quaternion[0], imu_.quaternion[1], imu_.quaternion[2],
                  imu_.quaternion[3]);
      RCLCPP_INFO(this->get_logger(), "Gyroscope -- wx: %f; wy: %f; wz: %f",
                  imu_.gyroscope[0], imu_.gyroscope[1], imu_.gyroscope[2]);
      RCLCPP_INFO(this->get_logger(), "Accelerometer -- ax: %f; ay: %f; az: %f",
                  imu_.accelerometer[0], imu_.accelerometer[1],
                  imu_.accelerometer[2]);
    }

    if (INFO_MOTOR) {
      // Info motor states
      // q: angluar (rad)
      // dq: angluar velocity (rad/s)
      // ddq: angluar acceleration (rad/(s^2))
      // tau_est: Estimated external torque

      for (int i = 0; i < 12; i++) {
        motor_[i] = data->motor_state[i];
        RCLCPP_INFO(this->get_logger(),
                    "Motor state -- num: %d; q: %f; dq: %f; ddq: %f; tau: %f",
                    i, motor_[i].q, motor_[i].dq, motor_[i].ddq,
                    motor_[i].tau_est);
      }
    }

    if (INFO_FOOT_FORCE) {
      // Info foot force value (int not true value)
      for (int i = 0; i < 4; i++) {
        foot_force_[i] = data->foot_force[i];
        foot_force_est_[i] = data->foot_force_est[i];
      }

      RCLCPP_INFO(this->get_logger(),
                  "Foot force -- foot0: %d; foot1: %d; foot2: %d; foot3: %d",
                  foot_force_[0], foot_force_[1], foot_force_[2],
                  foot_force_[3]);
      RCLCPP_INFO(
          this->get_logger(),
          "Estimated foot force -- foot0: %d; foot1: %d; foot2: %d; foot3: %d",
          foot_force_est_[0], foot_force_est_[1], foot_force_est_[2],
          foot_force_est_[3]);
    }

    if (INFO_BATTERY) {
      // Info battery states
      // battery current
      // battery voltage
      battery_current_ = data->power_a;
      battery_voltage_ = data->power_v;

      RCLCPP_INFO(this->get_logger(),
                  "Battery state -- current: %f; voltage: %f", battery_current_,
                  battery_voltage_);
    }
  }

  // Create the suber  to receive low state of robot
  rclcpp::Subscription<unitree_go::msg::LowState>::SharedPtr suber_;

  unitree_go::msg::IMUState imu_;          // Unitree go2 IMU message
  unitree_go::msg::MotorState motor_[12];  // Unitree go2 motor state message
  int16_t foot_force_[4]{};                // External contact force value (int)
  int16_t
      foot_force_est_[4]{};  // Estimated  external contact force value (int)
  float battery_voltage_{};  // Battery voltage
  float battery_current_{};  // Battery current
};

int main(int argc, char *argv[]) {
  rclcpp::init(argc, argv);  // Initialize rclcpp
  rclcpp::spin(
      std::make_shared<LowStateSuber>());  // Run ROS2 node which is make
                                           // share with low_state_suber class
  rclcpp::shutdown();
  return 0;
}