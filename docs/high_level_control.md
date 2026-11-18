# G1 高层控制：怎么让它"往那走"

> 配套脚本：`02b_high_level_move.py` ｜ 建议安排：接在第 2 节（运控 FSM）之后，20 分钟
> Go2 版本在 [go2/high_level_control.md](../go2/high_level_control.md)，讲的是同一件事，但接口差别很大。

前面第 2 节讲的是**状态**：站着、蹲着、坐着。机器人站着不动，只是"能站"。
这一节讲**运动**：给它一个速度，它真的往那个方向走。

## 1. 三层控制栈：你在哪一层

| 层 | 你给什么 | 谁在算 | 本课在哪 |
|---|---|---|---|
| 高层 High-level | "向前 0.3 m/s，转 0.2 rad/s" | 你（脚本） | **本节** |
| 中层 Mid-level | 步态、落脚点、MPC / WBC 解出的关节目标 | 机器人固件里的运控 | 不讲，黑盒 |
| 低层 Low-level | 每个关节的力矩 / 位置 | `LowCmd` | 不讲，只有 `LowState` 只读 |

关键认知：**SDK 只给你速度，不给你坐标。**

`LocoClient` 里没有 `GoTo(x, y)` 这种接口。为什么？因为"去 (3, 2) 那个点"需要里程计、
避障、判断到没到 —— 这些是应用层的事，厂商只保证"你说多快，它就走多快"。
所以本节最后 20 行代码，是我们自己写的第一个"导航"。

## 2. 一条指令长什么样

```python
client.SetVelocity(vx, vy, wz, duration)   # API 7105
```

| 参数 | 含义 | 单位 | 正方向 |
|---|---|---|---|
| `vx` | 前后 | m/s | 前 |
| `vy` | 左右 | m/s | 左 |
| `wz` | 转向 | rad/s | 逆时针（从上往下看） |
| `duration` | 预授权时长 | s | 到点固件自己停 |

"机体坐标系"这四个字是本课最大的坑：`vx=0.3` 永远是"朝着它现在脸朝的方向走 0.3"，
不是"朝地图东边走"。机器人转了 90°，同一个 `vx` 就变成朝北走了。

### `duration` 是 G1 的招牌设计

G1 的速度指令**自带时长**：`SetVelocity(0.3, 0, 0, 2.0)` 的意思是
"我预授权你以 0.3 m/s 走 2 秒"，2 秒到点它自己收住，不需要你叫停。

这带来一个非常直观的现象：**你断流了，它还在走。**
课上用 `--action dropout` 只发一条 `duration=3.0` 的指令，然后闭嘴 3 秒，
看着它一路走完 —— 学生第一次理解"授权"和"指令"不是一回事。

对比 Go2：`Move()` 没有 duration，断流几百毫秒固件就自己停。
两种设计都是安全考虑，但行为完全相反，值得各跑一次。

G1 还有个 `Move(vx, vy, vyaw, continous_move=False)`，是 `SetVelocity` 的语法糖：
`continous_move=True` 就是把 duration 设成 864000 秒（10 天），等于"一直走直到我叫停"。
注意上游把 continuous 拼成了 `continous`，写代码时照抄别纠正。

## 3. 前置状态：先进 FSM 500

速度指令只在主运控里有效。发之前必须先：

```python
client.SetFsmId(500)     # 进主运控
```

不在主运控里，`SetVelocity` 会返回 `7301`（运控服务没起来）或 `7302`（FSM ID 非法）。
`02b` 脚本里这一步是硬编码的，跑 `--action probe` 之外的动作都会先做一次。

## 4. 反馈从哪来

发指令是开环。要闭环，就得读：

```python
from unitree_sdk2py.idl.unitree_go.msg.dds_ import SportModeState_
sub = ChannelSubscriber("rt/sportmodestate", SportModeState_)
```

注意这里有个容易混的地方：**G1 的 `LowState` 是 `unitree_hg`，
`SportModeState` 却是 `unitree_go`。** 而且和 Go2 是**同一条** DDS 话题名
（ROS 2 里分别 remap 成 `/sportmodestate` 和 `/lf/sportmodestate`）。

用得到的字段：

| 字段 | 含义 | 单位 | 注意 |
|---|---|---|---|
| `position[0..1]` | 运控内部里程计估的世界坐标 | m | **会漂**，不是 SLAM 的 map 系 |
| `velocity[0..2]` | 机体坐标系线速度 | m/s | 方向跟着身体转 |
| `imu_state.rpy[2]` | yaw | rad | 漂移慢，短时间够用 |
| `gait_type` | 当前步态编号 | — | 静态走 / 正常步态不一样 |
| `mode` | 运控模式 | — | 掉出主运控时速度指令会被拒 |
| `foot_force[0..3]` | 四足触地力 | N | 判断是不是真的落地了 |

`position` 是步态里程计（腿的运动学 + IMU 融合），走十分钟能漂几十厘米到几米。
课堂做 1~2 米的到点演示够用，但绝不能当定位。要真定位得靠雷达 + SLAM（第 5+ 节）。

## 5. 自己写一个 MoveTo（本节的核心）

控制律只有四行。难点全在第一行：**把世界系误差转成机体系**。

```python
x, y, yaw = st.pose()
ex, ey = gx - x, gy - y                 # 世界系误差
c, s = math.cos(yaw), math.sin(yaw)
ex_b =  c * ex + s * ey                 # 转到机体系
ey_b = -s * ex + c * ey

vx = kp * ex_b                          # 远了走快，近了走慢
wz = kyaw * math.atan2(ey_b, ex_b)      # 朝误差方向转
```

为什么必须转？因为 `vx` 是机体系的。少乘这个旋转矩阵，机器人会自信地朝"世界系前方"走，
而它的"前方"早就不一样了 —— 现象是**绕着你画弧，永远到不了**。这是学生最常见的 bug，
课上故意留一个错误版本让他们跑跑看，比讲矩阵快。

工程上还要加三件事，脚本里都有：

1. **方向偏差大就原地转**（`|bearing| > 0.6 rad` 时 `vx=0`），四足侧移能力有限，硬走会画大弧；
2. **到点判定加死区**（`dist < 0.10 m` 就停），否则会在目标点附近来回抖；
3. **超时 + 反馈断流就停车**，位置控制失去反馈等于盲开。

## 6. 三个必讲的坑

**① 坐标系混用。** 上面那个画弧的 bug。判断方法：让它走直线，看 `position` 轨迹是不是直线。

**② 里程计漂移。** 原地转四圈再回来，`position` 不会回到原点。
所以 MoveTo 天然有累积误差 —— 真机上"到点"演示控制在 1~2 米内。

**③ 控制权被抢。** 手机 App、遥控器、`02_loco.py` 的另一个进程，谁最后发谁说了算。
现象是"指令发出去了，机器人不动、或者自己在走"。排查：看 `SportModeState.mode`，
或者 `client.GetFsmId()`。

## 7. 20 分钟怎么上

| 分钟 | 做什么 | 命令 |
|---|---|---|
| 0–3 | 只读，确认反馈通 | `--action probe` |
| 3–8 | 发一条速度，20 Hz 持续 2 秒 | `--action twist --vx 0.2 --duration 2` |
| 8–12 | 断流实验：只发一条 duration=3，看它走完 | `--action dropout --vx 0.2 --duration 3` |
| 12–17 | 前进 + 转向画圆 | `--action circle --vx 0.2 --wz 0.3 --duration 4` |
| 17–20 | 闭环到点 | `--action goto --x 1.0 --y 0.5` |

时间够的话，把 Go2 那台也叫过来跑 `go2/02b_high_level_move.py --action dropout`，
两个断流行为放在一起对比，是这一节最值钱的两分钟。

## 8. 作业

1. 把 `action_goto` 的 `kp` 从 0.8 改成 3.0，跑一次，解释为什么开始抖。
2. 删掉 `ex_b/ey_b` 那两行的旋转（直接用 `ex, ey`），跑一次，描述轨迹形状，说清原因。
3. 加一个"到点后用 `AudioClient` 说一句'到了'"的收尾（接第 4 节）。
4. 把 `goto` 改成走三个点 A→B→C 的折线，中途不停车。想想为什么中间那次不必停车。
5. 想清楚：如果 `--action dropout` 里 `duration=3`，但你在第 1 秒就想停，该发什么？（答案：`stop`）
