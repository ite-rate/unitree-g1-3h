# 3 小时真机速成：Unitree G1 × ROS 2 × SDK

`unitree-g1-3h` —— 一个可以单独 clone、单独上课的实操仓库。

给第一次接触机器人的同学。3 小时只做一件事：**让你亲手让 G1 站起来、走两步、挥个手、说句话，再看懂它身上的 29 个关节**。

- 不写控制器，不讲 SLAM，不碰低层电机。
- 每个脚本只 import 官方 `unitree_sdk2py` 和 `rclpy`，**不经过任何课程封装**。
- 仓库里带一份官方 SDK 副本（加好注释），运行时 import 的就是它，`Cmd/Ctrl + 点击` 直接看实现。
- 出问题时，报错就落在你眼前这几十行里，能顺着源码查下去。
- 真机演示和课后自己改，用的是同一份代码。

> 主线是 **G1**。早期写好的 Go2 版本完整保留在 [`go2/`](go2/README.md)，作为附加章节；
> 现场如果 G1 不够、临时换 Go2，可以直接用那一套。

学完你能：

1. 用 `ros2 topic` 看懂 G1 广播了什么，频率多少；
2. 用 `LocoClient` 切运控状态机：站、蹲、坐、走、挥手；
3. 用 `G1ArmActionClient` 做 16 个手臂动作，用 `AudioClient` 做 TTS、音量、RGB 灯带；
4. 自己解析一帧 `LowState`，读出 29 个关节的角度、速度、力矩、温度；
5. 知道 DDS、网卡、domain、QoS、FSM 这些词在真机上分别对应什么故障。

## 仓库结构

```
00_probe.py ... 07_demo_show.py   8 个 G1 脚本，可单独运行
go2/                              Go2 附加章节（原 8 个脚本，逻辑未改）
unitree_sdk2py/                   官方 SDK 完整副本（只加注释；运行时用的就是它）
ros2_nodes/                       unitree_ros2 的节点源码（Go2 + G1，阅读用，不参与编译）
scripts/install.sh                全新 Ubuntu 22.04 一键装环境
scripts/env.sh                    每开一个终端 source 一次
scripts/connect.py                选网卡、生成 DDS 配置、确认收到 /lowstate
docs/ros2_minimal.html            rclpy / Node / Topic 图解页（单文件，离线可开）
docs/sdk_reading_map.md           课程脚本 → 源码文件 的跳转地图
docs/real_robot_checklist.md      上课前逐项打勾的真机核对表
LICENSES/ · THIRD_PARTY_NOTICES.md 第三方源码来源、固定版本与许可证
out/                              运行时生成的 CSV，已 gitignore
```

---

## 课前 10 分钟：把链路打通

新机器先装环境（Ubuntu 22.04，课前完成，约 15–30 分钟）：

```bash
cd ~/unitree-g1-3h
bash scripts/install.sh
```

之后每开一个新终端，先执行：

```bash
cd ~/unitree-g1-3h
source scripts/env.sh
```

连真机（只需做一次），然后自检：

```bash
source scripts/env.sh
python3 scripts/connect.py --iface eth0     # 把 eth0 换成连机器人的网卡名
source scripts/env.sh

python3 00_probe.py
```

看到 `[通过] DDS 链路正常` 再往下。没有真机时，`00_probe.py` 会停在"一条都没收到"，
按它打印的 5 条依次查。

> 机器人默认网段 `192.168.123.0/24`（G1 机载地址以现场标注为准，常见 `.161`）。
> 你的有线网卡要有同网段静态 IP，且 DDS 走这块网卡。
>
> **G1 用 `unitree_hg` 消息，Go2 用 `unitree_go`。** 消息类型混了，一条也收不到。

---

## 时间表

| 时间 | 分钟 | 内容 | 跑什么 |
|---|---|---|---|
| 00:00–00:10 | 10 | 连接自检 | `00_probe.py` |
| 00:10–00:35 | 25 | ROS 2 最小模型：Node / Topic / Message / QoS | [图解页](docs/ros2_minimal.html)、`01_ros2_subscriber.py` |
| 00:35–01:00 | 25 | G1 运控 FSM：站、蹲、坐、走、挥手 | `02_loco.py` |
| 01:00–01:20 | 20 | 手臂 16 个预置动作 | `03_arm_actions.py` |
| 01:20–01:40 | 20 | 语音 TTS、音量、RGB 灯带、播放 wav | `04_audio_led.py` |
| 01:40–02:10 | 30 | 29 个关节：角度、速度、力矩、温度 | `05_joint_monitor.py` |
| 02:10–02:30 | 20 | `/lowstate` 与 `/lf/lowstate` 的频率、抖动 | `06_rate_table.py`、`ros2 topic hz` |
| 02:30–02:50 | 20 | 串成 30 秒演示 | `07_demo_show.py` |
| 02:50–03:00 | 10 | 作业与源码阅读路线 | `docs/sdk_reading_map.md` |

只有 2 小时：砍掉第 6 节，把 `06_rate_table.py` 留成课后作业。

---

## 1. ROS 2 最小模型（25 分钟）

先读图解页：[docs/ros2_minimal.html](docs/ros2_minimal.html)。它把 `rclpy`、Node、Topic、
Message、Publisher/Subscriber、DDS、QoS、spin 画成了 7 张图。

### 先看，不写

```bash
ros2 topic list | grep -E 'lowstate|api'
ros2 topic info /lowstate -v
ros2 interface show unitree_hg/msg/LowState
ros2 topic echo --once --field imu_state.rpy /lowstate
ros2 topic hz /lowstate
```

逐个解释：

- **Node**：一个进程里的一个参与者。`ros2 topic list` 背后也有一个临时节点。
- **Topic**：带名字的数据管道。`/lowstate` 就是机器人一直往外广播的整机状态。
- **Message**：管道里数据的结构。G1 的 `LowState` 里有 `motor_state[35]`、`imu_state`，**没有电池字段**。
- **QoS**：管道对"可靠/实时"的取舍。`-v` 能看到 publisher 的 QoS；订阅端不兼容就一条也收不到。
- **DDS**：ROS 2 下面的通信层。Unitree 机器人内部也用 DDS，所以 SDK 和 ROS 2 看到的是同一份数据。

名字对应关系：

```
SDK / DDS:   rt/lowstate
ROS 2:       /lowstate
```

`/lf/lowstate` 是同一份状态的低频版本，内容一样，频率更低。

### 再写一个原生订阅者

```bash
python3 01_ros2_subscriber.py
```

这 60 行就是 `rclpy` 的全部核心：

```python
self.create_subscription(LowState, "/lowstate", self.on_msg, 10)
rclpy.spin(node)
```

### 改坏它（先预测，再验证）

```bash
# 终端 A：正常跑
python3 01_ros2_subscriber.py

# 终端 B：换一个 ROS domain，再订阅
ROS_DOMAIN_ID=1 ros2 topic list
```

预测：B 能看到 `/lowstate` 吗？为什么？

再看一个更常见的：把 `scripts/env.sh` 里 `CYCLONEDDS_URI` 指向的网卡改错，或者直接用
`--iface` 指定 Wi-Fi 网卡。现象是 `ros2 topic list` 空、`00_probe.py` 收不到。
**问题不在代码，在 DDS 找不到对方。**

---

## 2. G1 运控：先理解 FSM（25 分钟）

G1 的运控不是"一个动作一个 API"，而是**切状态机**。先列能力：

```bash
python3 02_loco.py --list
```

单独做一个：

```bash
python3 02_loco.py --action start
python3 02_loco.py --action squat
python3 02_loco.py --action stand_up
python3 02_loco.py --action wave_hand
python3 02_loco.py --action move_forward
```

连做一串：

```bash
python3 02_loco.py --demo
```

每条指令默认会停下来等回车；课堂演示嫌慢就加 `--yes`（确认已清场）。

### FSM 动作表

| 名字 | FSM ID | 触发方法 | 机器人做什么 | 风险 |
|---|---|---|---|---|
| `zero_torque` | 0 | `SetFsmId(0)` | 零力矩，关节立刻失去支撑，会软倒 | 高 |
| `damp` | 1 | `Damp()` / `SetFsmId(1)` | 阻尼保护，关节变硬但不保持姿态 | 低 |
| `squat` | 2 | `SetFsmId(2)` | 蹲下（Python 版没有 `Squat()`） | 低 |
| `sit` | 3 | `Sit()` | 坐下 | 低 |
| `stand_up` | 4 | `SetFsmId(4)` | 从坐/蹲站起（Python 版没有 `StandUp()`） | 低 |
| `start` | 500 | `Start()` | 进入主运控，后面才能 `Move` / 手臂动作 | 低 |
| `squat2standup` | 706 | `Squat2StandUp()` | 从蹲姿站起 | 低 |
| `lie2standup` | 702 | `Lie2StandUp()` | 从仰躺站起，要求仰面、硬平地 | 高 |
| `standup2squat` | 706 | `StandUp2Squat()` | 上游和 `squat2standup` 共用 706 | 低 |
| `high_stand` / `low_stand` | — | `SetStandHeight()` | 站到最高 / 最低 | 低 |
| `wave_hand` / `wave_hand_turn` | — | `SetTaskId(0/1)` | 原地挥手 / 转身挥手 | 低 / 中 |
| `shake_hand_start` / `_end` | — | `SetTaskId(2/3)` | 开始 / 结束握手 | 中 |
| `move_forward` / `lateral` / `rotate` | — | `SetVelocity(...)` | 走 1 秒后自动停 | 中 |
| `stop_move` | — | `SetVelocity(0,0,0)` | 速度清零 | 低 |

`zero_torque` 和 `lie2standup` 必须额外加 `--allow-dangerous`。

### 背后发生了什么

`LocoClient` 不是直接控电机。它发一条 RPC：

```
rt/api/sport/request    unitree_api/Request
  api_id = 7101         # SetFsmId
  parameter = {"data": 500}
```

机器人固件里的运动服务收到后执行，再回 `rt/api/sport/response`，`code = 0` 表示接单成功。

常用的 API 号（完整表见 `unitree_sdk2py/g1/loco/g1_loco_api.py`）：

| 能力 | API | 方法 |
|---|---|---|
| 读当前 FSM | 7001 | `GetFsmId()` |
| 切 FSM | 7101 | `SetFsmId(id)` |
| 设站立高度 | 7104 | `SetStandHeight(h)` |
| 给速度 | 7105 | `SetVelocity(vx, vy, omega, duration)` |
| 挥手 / 握手 | 7106 | `SetTaskId(id)` |

### 一个必须讲清楚的坑

Python 版的语法糖 **不返回 code**：

```python
code = client.Damp()      # code 是 None，不是 0
```

因为 `Damp()` 里面只是 `self.SetFsmId(1)`，没有 `return`。
想拿返回码，就自己调 `client.SetFsmId(1)`。`02_loco.py` 为了打印 code，统一走 `SetFsmId`。

### 错误码怎么读

| code | 含义 |
|---|---|
| 0 | 成功 |
| 3102 | 请求没发出去（网卡 / DDS 配置） |
| 3104 | 等回复超时（机器人没在听，或当前状态不允许） |
| 3203 | 固件没实现这个接口（型号 / 版本不支持） |
| 3204 | 参数不对 |
| 7301 | LocoState 不可用（运控服务没起来） |
| 7302 | FSM ID 非法（这个机型不支持该状态） |
| 7303 | Task ID 非法（挥手 / 握手参数不对） |

非 0 时先做 `damp`，确认机器人站立、没被 App 或遥控器接管，再重试。

---

## 3. 手臂动作（20 分钟）

```bash
python3 03_arm_actions.py --list
python3 03_arm_actions.py --action "high wave"
python3 03_arm_actions.py --action "heart"
python3 03_arm_actions.py --id 27
python3 03_arm_actions.py --demo
```

### 16 个动作总表

| 名字 | ID | 中文 | 保持型 | 风险 |
|---|---|---|---|---|
| `release arm` | 99 | 释放/收回手臂 | 否 | 低 |
| `two-hand kiss` | 11 | 双手飞吻 | 否 | 低 |
| `left kiss` | 12 | 左手飞吻 | 否 | 低 |
| `right kiss` | 13 | 右手飞吻 | 否 | 低 |
| `hands up` | 15 | 双手举起 | 是 | 中 |
| `clap` | 17 | 拍手 | 否 | 低 |
| `high five` | 18 | 举手击掌 | 是 | 中 |
| `hug` | 19 | 拥抱姿势 | 是 | 中 |
| `heart` | 20 | 比心 | 是 | 中 |
| `right heart` | 21 | 右手比心 | 是 | 中 |
| `reject` | 22 | 拒绝手势 | 否 | 低 |
| `right hand up` | 23 | 举右手 | 否 | 低 |
| `x-ray` | 24 | 双手交叉成 X | 否 | 低 |
| `face wave` | 25 | 脸旁挥手 | 否 | 低 |
| `high wave` | 26 | 高举挥手 | 否 | 低 |
| `shake hand` | 27 | 握手 | 是 | 中 |

- 名字必须和 `action_map` 完全一致（含空格、连字符）；用 `--list` 最稳。
- 保持型动作做完不会自动收回，脚本默认补一条 `99 release arm`；想保持就加 `--hold`。
- 手臂动作只在 **FSM 500 / 501 / 801** 下可用（否则返回 `7404`）。脚本会先用 `GetFsmId()` 检查，
  不在范围就提示先跑 `02_loco.py --action start`。
- `7400` 是 `rt/armsdk` 被别的进程占用；`7401` 是手臂正持有上一个动作，先发 99 或重复同一动作。

---

## 4. 语音与灯（20 分钟）

```bash
python3 04_audio_led.py --get
python3 04_audio_led.py --volume 80
python3 04_audio_led.py --tts "大家好，我是 G1"
python3 04_audio_led.py --led 0 128 255
python3 04_audio_led.py --wav path/to/test.wav
python3 04_audio_led.py --demo
```

G1 的语音服务（`rt/api/voice/request`）：

| 能力 | API | 范围 / 参数 |
|---|---|---|
| TTS | 1001 | `text` + `speaker_id`（0 是默认音色） |
| 读音量 | 1005 | 返回 `{"volume": 0–100}` |
| 设音量 | 1006 | 0–100 |
| 设 RGB 灯带 | 1010 | R/G/B 各 0–255 |
| 播放 PCM | 1003 | JSON + 二进制 PCM |
| 停止播放 | 1004 | `app_name` |

几个必须讲清楚的点：

- TTS 是**机器人自己念**，不是播放你电脑上的音频；
- 播放 wav 只接受 **16 kHz / 单声道 / 16-bit PCM**。格式不对不会报错，只会没声音，
  所以脚本先解析 wav 头再发；
- 转换命令：`ffmpeg -i in.wav -ar 16000 -ac 1 -sample_fmt s16 out.wav`；
- 读源码时会看到上游 `TtsMaker` 的 `self.tts_index += self.tts_index` 是个自乘 bug，
  导致 index 恒为 0。不影响本课，但值得指出来。

---

## 5. 29 个关节（30 分钟）

```bash
python3 05_joint_monitor.py --seconds 10
python3 05_joint_monitor.py --joint 3
python3 05_joint_monitor.py --joint L_knee
python3 05_joint_monitor.py --csv out/joints.csv --seconds 60
```

一帧 `LowState` 里最重要的是 `motor_state[35]`：

| 字段 | 含义 |
|---|---|
| `q` | 关节角（rad） |
| `dq` | 关节角速度（rad/s） |
| `tau_est` | 估计力矩（N·m） |
| `temperature[2]` | 两路温度（C） |
| `vol` | 母线电压（V） |

关节顺序（29 DOF 机型）：

| 范围 | 部位 |
|---|---|
| 0–11 | 两条腿（髋 3 + 膝 + 踝 2，左右各 6） |
| 12–14 | 腰（yaw / roll / pitch） |
| 15–21 | 左臂（肩 3 + 肘 + 腕 3） |
| 22–28 | 右臂（同上） |

> 23 DOF 机型 / 腰部锁死的机型：13、14、20、21、27、28 无效。消息里仍有这些槽位，只是值没有意义。
> 脚本里用 `*` 标了出来。

课堂演示：让学生抬一下 G1 的手臂，看对应关节的 `q` 变化；再用手摸一下关节附近，
对比 `temperature`。这就是"感知"最原始的样子。

---

## 6. 频率、抖动（20 分钟）

```bash
python3 06_rate_table.py --seconds 10
```

G1 同时广播两份整机状态：

| topic | 内容 | 大致频率 |
|---|---|---|
| `rt/lowstate` | 高频整机状态，低层控制用 | 约 500 Hz |
| `rt/lf/lowstate` | 低频整机状态，看状态 / 记日志用 | 约 50 Hz |

输出里看三列：

- **Hz**：平均频率；
- **p50 / p95 间隔**：p95 远大于 p50，说明偶发卡顿；
- **抖动**：间隔的标准差。

然后用 ROS 2 对照：

```bash
ros2 topic hz /lowstate
ros2 topic hz /lf/lowstate
ros2 topic info /lowstate -v
```

同一个 DDS 网络，两边数字应该接近。差很多时，优先怀疑：

1. 回调里干了重活（比如在 `on_msg` 里写文件、画图）；
2. 队列太长，积压；
3. 终端和机器人不在同一网段，丢包重传。

> G1 的 Python SDK 没有 Go2 那样的 `VideoClient` / 点云开关。雷达和相机走机器人自带的
> ROS 2 话题，本课不展开；想学感知，去配套的 `unitree-robotics-lab`。

---

## 7. 串起来（20 分钟）

```bash
python3 07_demo_show.py --yes
```

顺序：读状态 → 灯蓝 / 音量 80 → TTS 开场 → 进入运控 → 蹲姿站起 → 挥手 → 手臂 `high wave`
→ 释放 → 前进 1 秒 → 停止 → 坐下 → 灯灭 → TTS 结束。

这就是一节课的"成品演示"。学生作业：把其中任意一步换掉，做出自己的 30 秒演示。

---

## 真机演示流程（教师用）

上课前先按 [真机核对清单](docs/real_robot_checklist.md) 过一遍，把"实测"列填掉。

课前：

- [ ] 机器人电量 > 50%，急停在手边；
- [ ] 场地清空，四周留 2 m，地面不滑；
- [ ] **手臂活动范围内没有桌子、屏幕、人**（G1 的手臂动作幅度比 Go2 大）；
- [ ] 网线/网卡配置好，`00_probe.py` 通过；
- [ ] 关掉手机 App 对机器人的占用；
- [ ] 提前跑一遍 `02_loco.py --demo` 和 `03_arm_actions.py --list`，确认固件支持这些动作。

演示顺序（约 12 分钟）：

1. `00_probe.py`：让大家看到整机状态的数字在跳；
2. `ros2 topic list` / `ros2 topic hz /lowstate`：把"topic"这个词落到屏幕上；
3. `02_loco.py --action start` → `squat` → `stand_up` → `wave_hand`：每做一次，回到代码指一下 FSM 号；
4. `03_arm_actions.py --action "high wave"`：让后排也能看到手臂；
5. `04_audio_led.py --led 0 128 255`、`--tts "..."`：灯和声音一起上；
6. `05_joint_monitor.py --joint L_knee`：抬一下腿，看 `q` 变；
7. `07_demo_show.py --yes`：完整跑一遍收尾。

兜底：

- 动作返回非 0：先 `02_loco.py --action damp`；还不行就跳过动作，用灯、TTS、关节监视完成演示；
- 手臂 7404：先 `02_loco.py --action start`；
- 没有声音：检查 wav 是否 16 kHz / mono / 16-bit；TTS 是否被 App 占用；
- 网络断了：回到 `00_probe.py` 的排障 5 条，不要在现场重装环境。

---

## G1 SDK 能力地图

| 能力 | 接口 | 底层 topic | 备注 |
|---|---|---|---|
| 整机状态 | `ChannelSubscriber` + `unitree_hg.LowState_` | `rt/lowstate` | 35 个电机槽位、IMU，无电池 |
| 低频状态 | 同上 | `rt/lf/lowstate` | 约 50 Hz |
| 运控 FSM | `LocoClient` | `rt/api/sport/request` | 站、蹲、坐、走、挥手 |
| 手臂动作 | `G1ArmActionClient` | `rt/api/arm/request` | 16 个预置动作 |
| 语音 / 灯 | `AudioClient` | `rt/api/voice/request` | TTS、音量、RGB、wav |
| 低层电机 | `LowCmd_` | `rt/lowcmd` | 本课不涉及，见配套 lab 课程 |
| 雷达 / 相机 | — | 机器人自带的 ROS 2 话题 | Python SDK 无对应 client |

> G1 的 `LowState` **没有电池字段**（Go2 才有 `bms_state`、`power_v`）。电量看 App。

---

## 为什么这些脚本不封装

每个文件都是"官方 import + argparse + 一段 main"，没有 `common` 模块、没有基类、没有额外抽象。
代价是有几段重复代码，收益是：

- 学生看到的 `ChannelSubscriber("rt/lowstate", LowState_)` 和官方示例一模一样；
- 报错行号就是真实调用点，不用在封装层里追；
- 想抄到自己的项目里，复制一个文件就能跑。

等他们把这 8 个文件跑熟，再去配套的 `unitree-robotics-lab` 里看 `common/` 为什么要封装，
才知道封装解决了什么问题。

---

## 想钻进去看源码：`Cmd/Ctrl + 点击` 就能跳

仓库里直接放了官方 SDK 完整副本 `unitree_sdk2py/`，以及 `unitree_ros2` 里最相关的节点
`ros2_nodes/`（Go2 + G1）。逻辑一行没改，只在关键位置加了中文注释：

- 每个注释过的文件开头都有 `课程阅读副本` 横幅，写明上游地址、固定版本、对应哪一节；
- 运行时 import 的就是仓库里这份，所以点击 `ChannelSubscriber`、`LocoClient`、`LowState_`，
  跳到的是你正在跑的代码；
- 完整对照表见 [源码阅读地图](docs/sdk_reading_map.md)，来源和许可证见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

最短的一条阅读路线（10 分钟）：

1. `unitree_sdk2py/core/channel.py` → `ChannelSubscriber`：DDS 是怎么被包成 topic 的；
2. `unitree_sdk2py/rpc/client_base.py` → `_CallBase`：Request 怎么发、Response 怎么等；
3. `unitree_sdk2py/g1/loco/g1_loco_client.py` → `SetFsmId()`：只有几行，API ID 就是 7101。

三处连起来，就是 `client.Start()` 这一句到底发生了什么。再看
`ros2_nodes/g1/g1_loco_client_example.cpp`，会发现 C++ 走 ROS 2 topic 用的是同一组 API ID。

---

## 排障表

| 现象 | 最可能的原因 | 一步检查 |
|---|---|---|
| `00_probe.py` 一条收不到 | 网卡 / CYCLONEDDS_URI / 机器人没开机 | `ip addr`；`ping 192.168.123.161`；`source scripts/env.sh` |
| 能收 Go2 但收不到 G1 | 消息类型用错（`unitree_go` vs `unitree_hg`） | 确认 import 的是 `unitree_hg` |
| `ros2 topic list` 空，但 SDK 能收 | ROS 的 RMW / domain 不对 | `echo $RMW_IMPLEMENTATION $ROS_DOMAIN_ID`；`ros2 daemon stop` |
| 动作 code=3102 | 请求没发出去 | 回到 `00_probe.py`，先确认链路 |
| 动作 code=3104 | 超时 / 当前状态不允许 | 先 `--action damp`；关掉 App 占用 |
| 动作 code=3203 | 固件不支持 | 换动作；查机器人型号和固件版本 |
| 动作 code=7302 | FSM ID 非法 | 换 `start` / `damp`；确认机型支持该状态 |
| 手臂 code=7404 | 当前 FSM 不是 500/501/801 | 先 `02_loco.py --action start` |
| 手臂 code=7401 | 手臂正持有上一个动作 | 先发 `release arm`（99），或重复同一动作 |
| LED / 音量 code=3204 | 参数超范围 | 音量 0–100；RGB 0–255 |
| TTS 没声音 | 音量 0 / App 占用 / 服务忙 | `--volume 80`；关 App；重试 |
| wav 没声音 | 不是 16 kHz / mono / 16-bit | `ffmpeg -ar 16000 -ac 1 -sample_fmt s16` |
| 频率比 `ros2 topic hz` 低很多 | 回调太重 / 队列积压 | 把解析移出回调；只存最新一帧 |
| 关节温度全 0 | 机器人待机 / 未上电 | 先 `start`；确认机器人已使能 |

---

## 作业

1. 改 `05_joint_monitor.py`：任意关节温度超过 55 C 时打印一行 `HOT: <name>`，并写进 CSV。
2. 改 `06_rate_table.py`：把 p95 抖动按 1 秒窗口画成文本柱状图，观察走起来和站着时的差别。
3. 用 `02_loco.py` + `03_arm_actions.py` + `04_audio_led.py` 拼一个 30 秒开场：
   灯渐亮 → 站起 → 挥手 → 比心 → TTS 报幕 → 灯渐暗。

---

## 附加：Go2 版本

Go2 的 8 个脚本、动作 API 表、激光雷达 / 相机 / 频率实验、排障表都保留在
[`go2/README.md`](go2/README.md)。它们和 G1 共用同一套 DDS / ROS 2 概念，只是消息类型
（`unitree_go`）、运控接口（`SportClient`）和感知能力不同。

---

## 继续往下学

这 3 小时只覆盖"用起来"。想理解背后的控制、桥接、建图与导航，去配套的
`unitree-robotics-lab`（19 节完整课程）：

- 低层 `LowCmd` 与关节控制；
- SDK → ROS 2 桥；
- 频率、延迟、rosbag；
- SLAM / Nav2 / 综合巡逻。
