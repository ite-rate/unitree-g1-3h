// =============================================================================
// 课程阅读副本 · 官方 unitree_ros2 例程，逻辑未改动，只加了注释
// 上游: https://github.com/unitreerobotics/unitree_ros2
// 版本: 668d1ec5a05d1c38d3306bdca7d59f2ba3581a88（与 scripts/install.sh 固定的一致）
// 本文件: ros2_nodes/read_wireless_controller.cpp
// 课程位置: 06_rate_table.py
//
// ▶ 订阅遥控器：ROS 2 里写 "/wirelesscontroller"，对应 DDS rt/wirelesscontroller。
//   不开遥控器就没有数据，topic 存在但 hz 为空 —— 正好用来讲“topic 存在 ≠ 有数据”。
//   仅阅读，不参与本仓库编译。
// =============================================================================
/**
 * This example demonstrates how to use ROS2 to receive wireless controller
 *states of unitree go2 robot
 **/
#include "rclcpp/rclcpp.hpp"
#include "unitree_go/msg//wireless_controller.hpp"

class WirelessControllerSuber : public rclcpp::Node {
 public:
  WirelessControllerSuber() : Node("wireless_controller_suber") {
    // the cmd_puber is set to subscribe "/wirelesscontroller" topic
    suber_ = this->create_subscription<unitree_go::msg::WirelessController>(
        "/wirelesscontroller", 10,
        [this](const unitree_go::msg::WirelessController::SharedPtr data) {
          topic_callback(data);
        });
  }

 private:
  void topic_callback(
      const unitree_go::msg::WirelessController::SharedPtr& data) {
    // lx: Left joystick x value
    // ly: Left joystick y value
    // rx: Right joystick x value
    // ry: Right joystick y value
    // keys value

    RCLCPP_INFO(
        this->get_logger(),
        "Wireless controller -- lx: %f; ly: %f; rx: %f; ry: %f; key value: %d",
        data->lx, data->ly, data->rx, data->ry, data->keys);
  }

  rclcpp::Subscription<unitree_go::msg::WirelessController>::SharedPtr suber_;
};

int main(int argc, char* argv[]) {
  rclcpp::init(argc, argv);  // Initialize rclcpp
  // Run ROS2 node which is make share with wireless_controller_suber class
  rclcpp::spin(std::make_shared<WirelessControllerSuber>());
  rclcpp::shutdown();
  return 0;
}