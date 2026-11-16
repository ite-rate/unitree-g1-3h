# 第三方源码说明

本仓库包含两份 Unitree 官方源码的副本，用于课堂阅读和运行：

| 目录 | 上游仓库 | 固定版本 | 许可证 |
|---|---|---|---|
| `unitree_sdk2py/` | <https://github.com/unitreerobotics/unitree_sdk2_python> | `814556d15970dd2ecf1c9984e845ca02ab07e206` | BSD 3-Clause |
| `ros2_nodes/` | <https://github.com/unitreerobotics/unitree_ros2> | `668d1ec5a05d1c38d3306bdca7d59f2ba3581a88` | BSD 3-Clause |

`ros2_nodes/` 现在包含 Go2 与 G1 两组例程（`ros2_nodes/*.cpp` 是 Go2，`ros2_nodes/g1/` 是 G1）。

许可证全文：

- `LICENSES/unitree_sdk2_python-LICENSE`
- `LICENSES/unitree_ros2-LICENSE`

## 改了什么

- **只加了注释**：Python 文件加 `#` 注释，C++ 文件加 `//` 注释，代码逻辑、结构、命名都没有改。
- 注释统一以 `课程阅读副本` 开头，写明上游地址、固定版本、对应课程脚本和阅读提示。
- `unitree_sdk2py/` 是完整包（含 a2/b2/g1/h1/h2 等其他机型），保证 import 行为和官方安装一致；G1 主线用到 `g1/` 与 `unitree_hg` 消息，Go2 附加章节用到 `go2/` 与 `unitree_go` 消息。
- G1 的 6 个 Python 文件（`unitree_sdk2py/g1/loco/g1_loco_api.py`、`g1_loco_client.py`、`unitree_sdk2py/g1/arm/g1_arm_action_api.py`、`g1_arm_action_client.py`、`unitree_sdk2py/g1/audio/g1_audio_api.py`、`g1_audio_client.py`）加了动作枚举级别的详细注释（每个动作 ID 的中文名、机器人行为、触发方式），同样只加注释不改逻辑。
- `ros2_nodes/g1/` 是 G1 的 C++ 阅读副本，覆盖运控 FSM、手臂动作、语音三个服务。

## 为什么放在仓库里

1. 学生 `Cmd/Ctrl + 点击` 能直接跳到真实实现，而不是 `.pyi` 或空壳；
2. 运行时 import 的就是这份副本，读到什么就跑的是什么；
3. 版本固定，不同机器上看到的是同一份代码。

## 升级时注意

`scripts/install.sh` 里的 `SDK2PY_SHA` / `ROS2_SHA` 必须和本文件的版本一致。
升级步骤：

```bash
# 1. 改 install.sh 里的两个 SHA
# 2. 重新执行安装
bash scripts/install.sh
# 3. 用新版本覆盖副本，并重新加注释（注释会丢，需要重跑标注）
```

如果不需要跟上游升级，保持现状即可。
