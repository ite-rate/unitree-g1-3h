# 真机核对清单（G1）

这套脚本的接口来自固定版本的官方源码（`unitree_sdk2_python` @ `814556d`、
`unitree_ros2` @ `668d1ec`），但**没有在真机上逐项跑过**。上课前请按下面顺序过一遍，
把"实测"填上；有出入就改脚本，不要改预期去迁就结果。

任何会动的步骤之前：清场、留 2 m、手握急停、确认机器人站立、**手臂活动范围内没有人或桌子**。

## A. 连接与 ROS 2

| # | 验证什么 | 步骤 | 预期 | 实测 |
|---|---|---|---|---|
| A1 | `/lowstate` 链路 | `python3 00_probe.py` | 收到数据；打印 `mode_machine`、IMU、电机温度；没有电量（G1 正常） | |
| A2 | ROS 2 能看到同一份数据 | `ros2 topic list`、`ros2 topic hz /lowstate` | `/lowstate` 存在，频率与 A1 接近 | |
| A3 | 原生订阅者 | `python3 01_ros2_subscriber.py` | 每秒打印累计条数、Hz、yaw、温度 | |
| A4 | 网卡改错会怎样 | `python3 00_probe.py --iface <错误网卡>` | 收不到，打印 5 条排障提示 | |
| A5 | 源码跳转到仓库副本 | `python3 -c "import unitree_sdk2py.core.channel as c; print(c.__file__)"` | 路径在 `unitree-g1-3h/unitree_sdk2py/` 下，不是 `site-packages` | |
| A6 | 消息类型没混 | `ros2 interface show unitree_hg/msg/LowState` | 能看到 `motor_state` / `imu_state`；Go2 的 `unitree_go` 不应被 G1 脚本使用 | |

## B. G1 运控 FSM

| # | 验证什么 | 步骤 | 预期 | 实测 |
|---|---|---|---|---|
| B1 | 阻尼 | `python3 02_loco.py --action damp` | `code=0`，关节变硬 | |
| B2 | 进入运控 | `--action start` | `code=0`，FSM 到 500 | |
| B3 | 蹲下 / 站起 | `--action squat`、`--action stand_up` | `code=0`，动作完整、无失稳 | |
| B4 | 蹲姿站起 | `--action squat2standup` | `code=0`；记录动作时长 | |
| B5 | 挥手 | `--action wave_hand` | `code=0`，手臂抬起挥动 | |
| B6 | 前进 1 秒 | `--action move_forward` | 前进约 0.2 m，自动停 | |
| B7 | 站高 / 站低 | `--action high_stand`、`--action low_stand` | `code=0`，高度变化明显 | |
| B8 | 危险动作拦截 | 不带 `--allow-dangerous` 跑 `zero_torque` | 脚本拒绝执行 | |
| B9 | 不支持的状态 | 手动试 `SetFsmId(999)` | 记录是否返回 `7302` | |

> `zero_torque` 会让机器人软倒，只在有垫子、有人保护时试；课堂默认不跑。

## C. 手臂动作

| # | 验证什么 | 步骤 | 预期 | 实测 |
|---|---|---|---|---|
| C1 | 动作表 | `python3 03_arm_actions.py --list` | 16 个动作，含 ID、中文、是否保持型 | |
| C2 | FSM 检查 | 在 `damp` 状态下跑 `--action "high wave"` | 提示 FSM 不在 500/501/801；执行返回 `7404` | |
| C3 | 高举挥手 | 先 `02_loco.py --action start`，再 `--action "high wave"` | `code=0`，手臂动作完整 | |
| C4 | 保持型 + 自动释放 | `--action "heart"` | 做比心，2 秒后自动 99 释放 | |
| C5 | 保持不释放 | `--action "heart" --hold` | 保持比心；再 `--action "release arm"` 收回 | |
| C6 | 手臂正持有 | 连续发两个不同动作，不加释放 | 第二次返回 `7401` | |
| C7 | 按 ID 执行 | `--id 26` | 与 `--action "high wave"` 等价 | |

## D. 语音、音量、灯带

| # | 验证什么 | 步骤 | 预期 | 实测 |
|---|---|---|---|---|
| D1 | 读音量 | `python3 04_audio_led.py --get` | 返回 `{"volume": 0–100}` | |
| D2 | 设音量 | `--volume 80`、`--volume 0` | 提示音变大 / 静音 | |
| D3 | TTS | `--tts "大家好，我是 G1"` | 机器人念出这句话 | |
| D4 | 灯带 | `--led 255 0 0`、`--led 0 0 0` | 变红 / 熄灭 | |
| D5 | 播放 wav | `--wav <16k/mono/16bit>.wav` | 有声音；不是这个格式时脚本拒绝并给 ffmpeg 命令 | |
| D6 | 综合 demo | `--demo` | 音量 80 → TTS → 红绿蓝 → 关灯 | |

## E. 关节与频率

| # | 验证什么 | 步骤 | 预期 | 实测 |
|---|---|---|---|---|
| E1 | 关节表 | `python3 05_joint_monitor.py --seconds 5` | 29 个关节，q/dq/tau/T 都有数 | |
| E2 | 单关节 | `--joint L_knee`，手动抬腿 | 只有左膝一行，`q` 随动作变化 | |
| E3 | CSV | `--csv out/joints.csv --seconds 10` | 文件有表头，行数约 10 × 29 | |
| E4 | 高频 / 低频 | `python3 06_rate_table.py --seconds 10` | 两路都有数；`/lowstate` 明显高于 `/lf/lowstate` | |
| E5 | 与 ROS 2 对照 | `ros2 topic hz /lowstate` | 与 E4 的 `rt/lowstate` 接近 | |
| E6 | 抖动 | 站着 vs 走着各跑一次 E4 | 记录 p95 与抖动差异 | |

## F. 综合演示

| # | 验证什么 | 步骤 | 预期 | 实测 |
|---|---|---|---|---|
| F1 | 全流程 | `python3 07_demo_show.py --yes` | 状态 → 灯/音量 → TTS → 站起 → 挥手 → 手臂 → 前进 → 坐下 → 收尾 | |
| F2 | 中途 Ctrl+C | 在挥手时按 Ctrl+C | 进入 `finally`，执行 `SetVelocity(0,0,0)` 与手臂 99 释放 | |
| F3 | 跳过前进 | `--no-walk` | 不移动，其余照常 | |

## 已经做过的离线检查

- 8 个 G1 脚本 + 8 个 Go2 脚本 `python3 -m py_compile` 通过。
- 用假的 `unitree_sdk2py` 模块跑过：`--list`、`--get`、连接失败分支、危险动作拦截、综合演示安全退出。
- 用上游 `example/g1/audio/test.wav` 验证了 RIFF/WAVE 解析（16 kHz / mono / 16-bit）。
- **没有**验证真实 DDS、RPC、运控 FSM、手臂动作、TTS、灯带；以上表格就是待办。
