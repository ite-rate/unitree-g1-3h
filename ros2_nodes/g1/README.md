# G1 C++ 阅读副本

Unitree 官方 `unitree_ros2` 的 G1 例程，逻辑未改，只加了中文注释（动作 ID、FSM、服务名均有标注）。

| 文件 | 对照课程 | 内容 |
|---|---|---|
| `loco_client_example.cpp` / `g1_loco_client.hpp` | `02_loco.py` | 运控 FSM、速度、挥手/握手 |
| `g1_arm_action_example.cpp` / `g1_arm_action_client.hpp` | `03_arm_actions.py` | 16 个预置手臂动作 |
| `g1_audio_client_example.cpp` / `g1_audio_client.hpp` | `04_audio_led.py` | TTS、音量、放音、RGB 灯带 |

只读原因：它们依赖上游 example 工程的 `include/`、`common/` 和 `unitree_api` 消息包，
本仓库没有 ROS 2 C++ 构建环境，放进来只为 Ctrl+点击 跳转阅读，不参与编译。
