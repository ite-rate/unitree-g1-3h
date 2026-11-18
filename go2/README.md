# 附加章节：Go2 版本（原 3 小时课程）

主线课程已经换成 **G1**（见仓库根目录 `README.md`）。这里保留最早写好的 Go2 版本，
作为附加内容——G1 现场不够、临时换 Go2 时可以直接用；也适合和 G1 对照着看：

- 同一个 DDS 网络，Go2 用 `unitree_go` 消息，G1 用 `unitree_hg`；
- 同一个 RPC 套路，Go2 是 `SportClient`，G1 是 `LocoClient` / `G1ArmActionClient`；
- Go2 有激光雷达和前置相机，G1 的 Python SDK 没有对应 client。

原 8 个脚本**逻辑一行没改**，只在文件头补了 3 行 `sys.path` 引导，保证从 `go2/` 目录直接运行
也能 import 到仓库根目录的 `unitree_sdk2py`。

另外新加了一个 `02b_high_level_move.py`（高层控制）。它和 G1 的 `02b` **是两个独立脚本**，
各用各的类（`SportClient` vs `LocoClient`），不共用一个 `--robot` 开关。

## 运行方式

先回到仓库根目录并载入环境：

```bash
cd ~/unitree-g1-3h
source scripts/env.sh
```

然后按原顺序跑：

```bash
python3 go2/00_probe.py
python3 go2/01_ros2_subscriber.py
python3 go2/02_actions.py --list
python3 go2/02b_high_level_move.py --action probe   # 高层控制，见下文
python3 go2/03_light_volume.py --get
python3 go2/04_lidar.py --seconds 10
python3 go2/05_camera.py
python3 go2/06_rate_table.py --seconds 10
python3 go2/07_demo_show.py --yes
```

也可以进入目录再跑（脚本自己会把仓库根加进 `sys.path`）：

```bash
cd go2
python3 00_probe.py
```

## Go2 时间表（原版）

| 时间 | 分钟 | 内容 | 跑什么 |
|---|---|---|---|
| 00:00–00:10 | 10 | 连接自检 | `00_probe.py` |
| 00:10–00:35 | 25 | ROS 2 最小模型：topic / msg / QoS | `ros2 topic ...`、`01_ros2_subscriber.py` |
| 00:35–01:10 | 35 | SDK 预设动作：打招呼、跳舞、走两步 | `02_actions.py` |
| 01:10–01:25 | 15 | 头部 LED 与音量 | `03_light_volume.py` |
| 01:25–02:05 | 40 | 激光雷达：自己解析 PointCloud2 | `04_lidar.py` |
| 02:05–02:35 | 30 | 前置摄像头：JPEG 字节流 | `05_camera.py` |
| 02:35–02:55 | 20 | topic 频率、抖动、带宽 | `06_rate_table.py` |
| 02:55–03:00 | 5 | 串起来 + 作业 | `07_demo_show.py` |

想在 Go2 上加高层控制：把上面的 35 分钟预设动作压到 25 分钟，中间插 20 分钟跑
`go2/02b_high_level_move.py`（讲解见 [high_level_control.md](high_level_control.md)）。

## 高层控制（Go2 自己的脚本）

```bash
python3 go2/02b_high_level_move.py --action probe
python3 go2/02b_high_level_move.py --action twist --vx 0.3 --duration 2
python3 go2/02b_high_level_move.py --action dropout      # 走一会儿 → 闭嘴 1.5 s，看它自己停
python3 go2/02b_high_level_move.py --action circle --vx 0.2 --wz 0.3 --duration 4
python3 go2/02b_high_level_move.py --action goto --x 1.0 --y 0.5
```

和第 2 节预设动作的区别：那一节是"一个 API 一个技能"，这一节是自己连续控速。

三个和 G1 完全不同的点（讲解见 [high_level_control.md](high_level_control.md)）：

- `Move()` 是 `_CallNoReply`，**没有回执**，返回值永远是 0，别拿它判断成败；
- `Move()` **没有 duration**，想连续走必须自己按 20 Hz 重发；
- 断流之后几百毫秒固件自己停 —— 所以高层控制是一条**数据流**，不是一次函数调用。

G1 反过来：`SetVelocity(..., duration)` 带预授权时长，断流了它会把这段走完。

## Go2 预设动作（`SportClient`）

```bash
python3 go2/02_actions.py --action balance
python3 go2/02_actions.py --action hello
python3 go2/02_actions.py --action stretch
python3 go2/02_actions.py --action dance1
python3 go2/02_actions.py --action heart
python3 go2/02_actions.py --action walk
python3 go2/02_actions.py --action demo
```

`SportClient` 不是直接控电机。它往 `rt/api/sport/request` 发一条 `unitree_api/Request`，
`api_id` 是动作编号，机器人固件里的运动服务执行后回 `rt/api/sport/response`。

| 动作 | API | 方法 |
|---|---|---|
| 阻尼 | 1001 | `Damp()` |
| 站稳 | 1002 | `BalanceStand()` |
| 停止移动 | 1003 | `StopMove()` |
| 站起 / 趴下 | 1004 / 1005 | `StandUp()` / `StandDown()` |
| 恢复站立 | 1006 | `RecoveryStand()` |
| 移动 | 1008 | `Move(vx, vy, vyaw)` |
| 坐下 / 起立 | 1009 / 1010 | `Sit()` / `RiseSit()` |
| 打招呼 | 1016 | `Hello()` |
| 伸懒腰 | 1017 | `Stretch()` |
| 跳舞 1 / 2 | 1022 / 1023 | `Dance1()` / `Dance2()` |
| 比心 | 1036 | `Heart()` |

翻转、跳跃类动作默认被脚本拦住，必须 `--allow-dangerous`。课堂演示不要做，除非有垫子和保护人员。

## Go2 头部 LED 与音量（`VuiClient`）

```bash
python3 go2/03_light_volume.py --get
python3 go2/03_light_volume.py --brightness 10
python3 go2/03_light_volume.py --volume 3
python3 go2/03_light_volume.py --demo
```

| 能力 | API | 范围 |
|---|---|---|
| 亮度 | 1005 / 1006 | 0–10 |
| 音量 | 1003 / 1004 | 0–10 |
| VUI 开关 | 1001 / 1002 | 0 / 1 |

- 亮的是**头部那颗白色 LED**，不是全身 RGB 灯带；
- 音量控制的是机器人内置提示音/语音，这版 Go2 SDK 没有"播放任意音频文件"的 client；
- 实时音频走 WebRTC（手机 App 那一套），不在 SDK2 的 DDS 接口里。

## Go2 激光雷达

```bash
python3 go2/04_lidar.py --seconds 10
python3 go2/04_lidar.py --seconds 10 --plot
```

输出大概长这样（数字以实测为准）：

```
已收 93 帧 | 本帧 20160 点 | 最近 0.42 m @ -37° | 前方 1.18 m
```

`/utlidar/cloud` 是标准 `sensor_msgs/PointCloud2`：

| 字段 | 含义 |
|---|---|
| `width` × `height` | 点数（雷达通常是单行，`height = 1`） |
| `point_step` | 每个点占几字节 |
| `fields[]` | 每个字段的名字和字节偏移（`x`、`y`、`z`、`intensity`…） |
| `data[]` | 所有点的二进制，按 `point_step` 切开 |

**不要硬编码 12 或 16 字节**。不同固件的点云可能多带 `intensity`、`ring`、`time`，
`point_step` 会变；按 `fields[].offset` 取才稳。

把雷达关掉再看 topic，是这节最值得做的实验：

```bash
# 终端 A
ros2 topic hz /utlidar/cloud
# 终端 B
python3 go2/04_lidar.py --switch off
python3 go2/04_lidar.py --switch on
```

**topic 存在 ≠ 有数据。** `ros2 topic list` 能列出来，但发布端没在发，`hz` 就是空的。

## Go2 前置摄像头

```bash
python3 go2/05_camera.py
python3 go2/05_camera.py --frames 30
```

- `VideoClient.GetImageSample()` 一次 RPC 换一帧 **JPEG 字节流**，不是持续视频流；
- FPS 受网络往返、JPEG 编码、机器人负载影响，不是相机标称帧率；
- 想预览：`sudo apt install python3-opencv`，再 `--show`。
  **不要 `pip install opencv-python`**，它会升级 numpy，弄坏 ROS 2 Humble 的 `rclpy`；
- 取图失败先看机器人 App 是否占着相机，再看网络。

## Go2 频率表

```bash
python3 go2/06_rate_table.py --seconds 10
```

| topic | 内容 |
|---|---|
| `rt/lowstate` | 电机、IMU、电池，高频 |
| `rt/sportmodestate` | 运控状态，中频 |
| `rt/utlidar/cloud` | 点云，大包 |
| `rt/wirelesscontroller` | 遥控器（不开遥控器就没有） |

用 ROS 2 对照：

```bash
ros2 topic hz /lowstate
ros2 topic hz /sportmodestate
ros2 topic bw /utlidar/cloud
ros2 topic info /utlidar/cloud -v
```

频率差很多时，优先怀疑：回调里干了重活、队列太长积压、终端和机器人不在同一网段。

## Go2 综合演示

```bash
python3 go2/07_demo_show.py --yes
```

顺序：读状态 → 灯 10 / 音量 8 → 站稳 → 打招呼 → 伸懒腰 → 跳舞 → 拍照 → 雷达 5 秒
→ 恢复灯光音量。

## Go2 排障表

| 现象 | 最可能的原因 | 一步检查 |
|---|---|---|
| `00_probe.py` 一条收不到 | 网卡 / CYCLONEDDS_URI / 机器人没开机 | `ip addr`；`ping 192.168.123.161`；`source scripts/env.sh` |
| `ros2 topic list` 空，但 SDK 能收 | ROS 的 RMW / domain 不对 | `echo $RMW_IMPLEMENTATION $ROS_DOMAIN_ID` |
| 动作 code=3102 | 请求没发出去 | 回到 `00_probe.py` |
| 动作 code=3104 | 超时 / 当前状态不允许 | 先 `--action balance`；关 App |
| 动作 code=3203 | 固件不支持 | 换动作；查型号和固件 |
| LED / 音量 code≠0 | VUI 服务不可用或参数超范围 | 参数 0–10；重启机器人 |
| 点云一帧都没有 | 雷达被关 / topic 不支持 | `--switch on`；`ros2 topic list \| grep utlidar` |
| 点云有帧但点数为 0 | 解析偏移不对 / 全被过滤 | 打印 `msg.point_step`、`msg.fields` |
| 相机 code≠0 | videohub 忙 / App 占相机 | 关 App；重试 |
| `Move` 没反应 | 没进运控 / 遥控器接管 | 先 `balance`；松开遥控器；再 `walk` |

## 和 G1 的差异

| 项目 | Go2（本章） | G1（主线） |
|---|---|---|
| 状态消息 | `unitree_go/msg/LowState` | `unitree_hg/msg/LowState` |
| 电机数量 | 12（`motor_state[20]`，前 12 有效） | 29（`motor_state[35]`，前 29 有效） |
| 电池 | `bms_state.soc`、`power_v` | 不在 `LowState` 里 |
| 预设动作 | `SportClient`，API 1001–2045 | `LocoClient`，FSM 0–706 + `Move/SetVelocity` |
| 手臂动作 | 无独立接口 | `G1ArmActionClient`，16 个动作 |
| 语音/灯 | `VuiClient`（亮度/音量 0–10） | `AudioClient`（TTS、音量 0–100、RGB、wav） |
| 雷达/相机 | `PointCloud2` + `VideoClient` | SDK 没有对应 client，走自带 ROS 2 话题 |
