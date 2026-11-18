# Go2 高层控制：怎么让狗"往那走"

> 配套脚本：`go2/02b_high_level_move.py` ｜ 建议安排：接在 Go2 预设动作（`02_actions.py`）之后，20 分钟
> G1 版本在 [../docs/high_level_control.md](../docs/high_level_control.md)。

和第 2 节的区别：那一节讲的是**预设动作**（打招呼、跳舞，一个 API 一个技能），
这一节讲的是**自己连续控速**：给它 `vx/vy/vyaw`，它就一直按这个速度走。

## 1. 一条指令长什么样

```python
client.Move(vx, vy, vyaw)     # API 1008，service "sport"
```

| 参数 | 含义 | 单位 | 正方向 |
|---|---|---|---|
| `vx` | 前后 | m/s | 前 |
| `vy` | 左右 | m/s | 左 |
| `vyaw` | 转向 | rad/s | 逆时针（从上往下看） |

三个数都在**机体坐标系**（x 前、y 左、右手系）。狗转了 90°，同一个 `vx` 就变成朝另一个方向走。
这是学生第一个 bug 的固定来源。

## 2. 狗和人最大的差别：`Move()` 没有回执，也没有时长

这是本节的灵魂，值得单独一屏。

```python
# unitree_sdk2py/go2/sport/sport_client.py
def Move(self, vx, vy, vyaw):
    p = {"x": vx, "y": vy, "z": vyaw}
    code = self._CallNoReply(SPORT_API_ID_MOVE, json.dumps(p))
    return code        # ← 永远是 0，它只是"包发出去了"
```

三件事要讲清：

1. **`_CallNoReply`**：UDP 包扔出去，不等回复、不重传。返回值 0 不代表狗收到了，
   只代表你的网卡把包发出去了。所以 `if client.Move(...) == 0: print("成功")` 是错的。
2. **没有 duration**：这是"一次性小步指令"，走一小段就停。想连续走，必须自己按频率重复发。
3. **超时保护在固件里**：你停止发指令，几百毫秒后它自己停下。
   这不是 bug，是安全设计 —— 控制程序崩了，狗不能永远朝墙走。

所以本节的中心句是：

> **高层控制是一条持续的数据流，不是一次函数调用。**

G1 完全是另一套：`SetVelocity(vx, vy, wz, duration)` 带时长，断了指令它会把这段走完。
两边各跑一次 `dropout`，学生自己就能说出"授权"和"心跳"的区别。

（具体断流阈值随固件版本略有差别，`--action dropout` 就是拿真机测这个数。）

## 3. 前置状态：先站稳

```python
client.BalanceStand()    # 1002，站稳
```

和 G1 的 `SetFsmId(500)` 对应，但 Go2 这边叫平衡站立，不是切 FSM。
没站稳就 `Move`，常见结果是原地踏步或者不动。

## 4. 反馈从哪来

```python
from unitree_sdk2py.idl.unitree_go.msg.dds_ import SportModeState_
sub = ChannelSubscriber("rt/sportmodestate", SportModeState_)
```

| 字段 | 含义 | 单位 | 注意 |
|---|---|---|---|
| `position[0..1]` | 运控里程计的世界坐标 | m | **会漂** |
| `velocity[0..2]` | 机体坐标系线速度 | m/s | 方向跟着身体转 |
| `imu_state.rpy[2]` | yaw | rad | 短时间够用 |
| `gait_type` | 当前步态编号 | — | FreeWalk / trot 不一样 |
| `mode` | 运控模式 | — | 掉出运控时速度指令被拒 |
| `foot_force[0..3]` | 四足触地力 | N | 判断真的落地了没 |
| `range_obstacle[0..3]` | 四向避障距离 | m | 头部雷达辅助，本课不用 |

`position` 是步态里程计，走十分钟能漂几十厘米到几米。课堂做 1~2 米到点够用，不能当定位。

## 5. 自己写一个 MoveTo

SDK 没有 `GoTo(x, y)`。控制律四行：

```python
x, y, yaw = st.pose()
ex, ey = gx - x, gy - y                 # 世界系误差
c, s = math.cos(yaw), math.sin(yaw)
ex_b =  c * ex + s * ey                 # ★ 转到机体系
ey_b = -s * ex + c * ey

client.Move(kp * ex_b, 0.4 * ey_b, kyaw * math.atan2(ey_b, ex_b))
```

少写那条旋转，狗会自信地朝"世界系前方"走，现象是**绕着你画弧，永远到不了**。
另外方向偏差大（`> 0.6 rad`）就先原地转，侧移能力有限，硬走会画大弧。

## 6. 三个必讲的坑

**① 拿 `Move()` 的返回值判断成败。** 它永远 0，因为它不等回复。想确认真的在走，只能看 `velocity`。

**② 一次性调用就想让它一直走。** `client.Move(0.3, 0, 0)` 之后什么都不做，狗走一小段就停。
必须放进 20 Hz 循环。

**③ 停机方式。** 用 `StopMove()`（1003），不要指望 `Move(0,0,0)` —— 后者要靠固件把 0 当指令处理，
不如直接叫停干净。脚本的 `finally` 里就是 `StopMove()`。

## 7. 20 分钟怎么上

| 分钟 | 做什么 | 命令 |
|---|---|---|
| 0–3 | 只读，确认反馈通 | `--action probe` |
| 3–8 | 20 Hz 连续发速度 | `--action twist --vx 0.3 --duration 2` |
| 8–12 | **断流实验：闭嘴 1.5 秒看它自己停** | `--action dropout` |
| 12–17 | 前进 + 转向画圆 | `--action circle --vx 0.2 --wz 0.3 --duration 4` |
| 17–20 | 闭环到点 | `--action goto --x 1.0 --y 0.5` |

## 8. 作业

1. 把 `twist` 里的 `--hz` 从 20 改成 2，跑一次。描述狗的动作，解释为什么"抖"。
2. 在 `action_twist` 里打印每次 `Move()` 的返回值。观察它永远是 0，然后说清为什么不能拿它判断。
3. 删掉 `ex_b/ey_b` 的旋转，跑 `goto`，描述轨迹形状。
4. 用 `foot_force` 判断狗有没有真的四条腿落地，加一行提示。
