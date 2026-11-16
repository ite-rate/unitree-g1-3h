#!/usr/bin/env bash
# 每个新终端执行一次:  source scripts/env.sh
# 作用: 载入 ROS 2 Humble、Unitree 消息、SDK，并决定 DDS 走哪块网卡。
_REPO="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
export UNITREE_3H_REPO="$_REPO"

[ -f "$_REPO/config/local_paths.env" ] && . "$_REPO/config/local_paths.env"
: "${UNITREE_3H_WS:=$HOME/unitree_3h_ws}"
: "${UNITREE_3H_DEPS:=$HOME/unitree_3h_deps}"
export UNITREE_3H_WS UNITREE_3H_DEPS

. /opt/ros/humble/setup.bash
[ -f "$UNITREE_3H_WS/install/setup.bash" ] && . "$UNITREE_3H_WS/install/setup.bash"

export PATH="$HOME/.local/bin:$PATH"
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp   # 机器人和 ROS 2 两边都用 CycloneDDS
export ROS_DOMAIN_ID=0                          # Unitree 默认 domain 0
unset ROS_LOCALHOST_ONLY

# 让仓库根目录优先于 site-packages，保证 import 到的是仓库里的 unitree_sdk2py 副本。
# 这样在 go2/ 子目录里运行脚本时，也不会跳到 ~/.local 的版本。
export PYTHONPATH="$_REPO:${PYTHONPATH:-}"

if [ -f "$_REPO/config/cyclonedds.env" ]; then
  . "$_REPO/config/cyclonedds.env"
  echo "[g1-3h] 网卡=$UNITREE_3H_IFACE  RMW=$RMW_IMPLEMENTATION"
else
  echo "[g1-3h] 还没选网卡。连真机先跑: python3 scripts/connect.py --iface <网卡名>，然后重新 source"
fi
unset _REPO
