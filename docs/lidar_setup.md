# 激光雷达前置条件：让 Livox MID-360S 的点云出现在网络上

`08_lidar.py` 只是一个订阅者，它自己不会去"打开"雷达。
雷达是一台独立的网络设备，要先有一个**驱动**把它的数据收下来、发成 topic，脚本才有东西可读。

```
MID-360S（头部，网口）  --UDP-->  livox_ros_driver2（你的笔记本）  --DDS topic-->  08_lidar.py
                                   依赖 Livox-SDK2                    /livox/lidar
```

所以前置条件就是三件事：**编译 SDK → 编译驱动 → 启动驱动**。每台电脑只需要编译一次，每次上课只需要启动。

> 环境：Ubuntu 22.04 + ROS 2 Humble（和本课 `scripts/install.sh` 装的一致）。

---

## 0. 网络：先能 ping 通雷达

笔记本插网线到机器人，有线网卡设成 `192.168.123.x`（掩码 255.255.255.0），然后：

```bash
ping 192.168.123.120
```

`.120` 是宇树文档里 G1 头部雷达的出厂地址。MID-360S 以你手上这台为准：ping 不通就用 Livox Viewer 2
（在你自己的电脑上运行，不要在机器人上运行）查一下雷达的实际 IP。

记下两个地址，第 3 步要用：

- 雷达 IP：例如 `192.168.123.120`
- 笔记本有线网卡 IP：例如 `192.168.123.222`（`ip addr` 查）

## 1. 编译安装 Livox-SDK2（一次）

驱动依赖这个 C++ SDK。MID-360S 是新型号，用 **master 分支的最新版**，老版本不认识它。

```bash
cd ~
git clone https://github.com/Livox-SDK/Livox-SDK2.git
cd Livox-SDK2 && mkdir build && cd build
cmake .. && make -j
sudo make install          # 装到 /usr/local/lib 和 /usr/local/include
```

## 2. 编译 livox_ros_driver2（一次）

```bash
mkdir -p ~/ws_livox/src
git clone https://github.com/Livox-SDK/livox_ros_driver2.git ~/ws_livox/src/livox_ros_driver2
source /opt/ros/humble/setup.bash
cd ~/ws_livox/src/livox_ros_driver2
./build.sh humble          # 参数必须是 humble；脚本会在 ~/ws_livox 下 colcon build
```

## 3. 改配置：告诉驱动雷达在哪、数据发给谁（一次）

MID-360S 用的配置文件是 `config/MID360s_config.json`（注意不是 `MID360_config.json`）。改两处：

```jsonc
"host_net_info" : [ { "host_ip" : "192.168.123.222", ... } ],   // 笔记本 IP
"lidar_configs" : [ { "ip" : "192.168.123.120", ... } ]          // 雷达 IP
```

```bash
cd ~/ws_livox/src/livox_ros_driver2
nano config/MID360s_config.json
./build.sh humble          # 配置文件是编译时拷进 install 的，改完要重新编译一次
```

## 4. 启动驱动（每次上课）

```bash
source ~/unitree-g1-3h/scripts/env.sh          # 和课程脚本用同一个 RMW 和 domain
source ~/ws_livox/install/setup.bash
ros2 launch livox_ros_driver2 rviz_MID360s_launch.py
```

用 `rviz_MID360s_launch.py`，不要用 `msg_MID360s_launch.py`：

| launch 文件 | 发出来的格式 | 能不能被 `08_lidar.py` 读 |
|---|---|---|
| `rviz_MID360s_launch.py` | 标准 `PointCloud2`，同时打开 RViz | 能 |
| `msg_MID360s_launch.py` | Livox 自定义消息 `CustomMsg`（给 FAST-LIO 等算法用） | 不能 |

先 `source scripts/env.sh` 是为了让驱动也用 CycloneDDS、domain 0，和 `08_lidar.py` 在同一个 DDS 网络里。

## 5. 验证，再跑课程脚本

```bash
ros2 topic hz /livox/lidar      # 应该约 10 Hz
python3 08_lidar.py             # 默认订阅 rt/livox/lidar（就是 ROS 2 的 /livox/lidar）
```

RViz 里能看到点云、`ros2 topic hz` 有数，`08` 就一定能收到。

---

## 收不到时按顺序查

1. `ping` 雷达 IP 通不通（第 0 步）；
2. 驱动终端有没有报错，常见的是 `host_ip` 写成了别的网卡的地址；
3. `ros2 topic list | grep livox` 有没有 `/livox/lidar`；
4. 用的是不是 `rviz_MID360s_launch.py`（`msg_` 版本发的是自定义格式）；
5. 驱动和 `08` 是不是都 source 了 `scripts/env.sh`（RMW、domain 要一致）。

## 另一条路：机器人自带的雷达服务

宇树文档里，G1 固件自带一个雷达服务（要求雷达驱动版本 ≥ 1.0.0.5），它直接把点云发到
`rt/utlidar/cloud_livox_mid360`，不需要你编译任何东西：

```bash
python3 08_lidar.py --topic rt/utlidar/cloud_livox_mid360
```

这份文档写的是 MID-360；换成 MID-360S 的机器上是否同样提供，先 `ros2 topic list | grep utlidar` 确认。
**两条路二选一**：雷达同一时间只把数据发给配置好的那台主机，自己的驱动和机器人自带服务同时跑可能互相抢。
