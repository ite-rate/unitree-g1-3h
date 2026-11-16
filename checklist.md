# 验收清单：G1 主课改造

对应 [spec.md](spec.md) 与 [tasks.md](tasks.md)。全部通过后 `[x]`。

## 结构

- [x] 根目录只有 G1 的 8 个脚本，Go2 的 8 个脚本在 `go2/`
- [x] `go2/` 下每个脚本都能 import 到根目录的 `unitree_sdk2py`（3 行 sys.path 引导）
- [x] `go2/README.md` 说明这是附加章节，并列出与 G1 的差异

## 脚本

- [x] `00_probe.py` 订阅 `rt/lowstate`，用 `unitree_hg.LowState`，不打印电量
- [x] `01_ros2_subscriber.py` 用 `rclpy` + `unitree_hg.msg.LowState`，可 `ros2 topic echo` 对照
- [x] `02_loco.py --list` 输出完整 FSM 表（0/1/2/3/4/500/702/706 + SetStandHeight/SetTaskId/SetVelocity）
- [x] `02_loco.py` 危险动作必须 `--allow-dangerous`，`finally` 里 `SetVelocity(0,0,0)`
- [x] `03_arm_actions.py --list` 输出 16 个动作的名字/ID/中文/保持型/风险
- [x] `03_arm_actions.py` 执行前用 `GetFsmId()` 校验，7400/7401/7402/7404 有中文解释
- [x] `04_audio_led.py` 支持 `--get/--volume/--tts/--speaker/--led/--wav/--demo`
- [x] `04_audio_led.py --wav` 能解析上游 `test.wav`（16000 Hz / 1 声道 / 16 bit），非此格式有提示
- [x] `05_joint_monitor.py` 覆盖 29 个关节，`--joint` 支持编号与名字，`--csv` 列头正确
- [x] `06_rate_table.py` 同时统计 `rt/lowstate` 与 `rt/lf/lowstate` 的 Hz / p50 / p95 / 抖动
- [x] `07_demo_show.py` 收不到 `/lowstate` 时拒绝动作，Ctrl+C 后仍执行收尾

## 注释

- [x] G1 六个 SDK 文件（loco/arm/audio 各 api + client）顶部有 `课程阅读副本` 横幅
- [x] 动作枚举逐条标注：名字 / ID / 中文 / 机器人行为 / 触发方法 / 风险
- [x] `git diff` 层面只有注释变化：AST 与上游逐文件对比结果 `SAME`
- [x] `ros2_nodes/g1/` 三个 C++ 例程 + 三个 `.hpp` 副本，去掉注释后与上游一致

## 文档

- [x] `README.md`：G1 主线、时间表、FSM 表、16 动作表、语音灯表、关节表、排障表、Go2 附加入口
- [x] `docs/ros2_minimal.html`：单文件离线，7 张内联 SVG，无 `http(s)://` 资源引用，标签闭合
- [x] `docs/sdk_reading_map.md` 中引用的路径全部存在
- [x] `docs/real_robot_checklist.md` 覆盖连接 / 运控 / 手臂 / 语音灯 / 关节 / 综合演示
- [x] `THIRD_PARTY_NOTICES.md` 已补 G1 Python 注释与 `ros2_nodes/g1/`

## 验证

- [x] `python3 -m py_compile` 全部脚本通过
- [x] `bash -n scripts/*.sh` 通过
- [x] 假 SDK 烟测：7 个脚本 `--help`、`02 --list/--action/--demo`、`03 --list/--action`、`04 --get/--tts/--led/--wav`、`05`、`06`、`07` 全部跑通
- [x] Markdown 相对链接 0 死链
