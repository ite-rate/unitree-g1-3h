#!/usr/bin/env bash
# Unitree G1 3 小时真机速成：一键安装
# 用法:  bash scripts/install.sh
# 目标机: 全新的 Ubuntu 22.04 (x86_64)，VMware / OrbStack / 实体机均可。可重复执行。
#
# 可选环境变量:
#   UNITREE_3H_MIRROR=auto|cn|official   软件源（默认 auto：连不上 pypi.org 就用清华源）
#   UNITREE_3H_DEPS=~/unitree_3h_deps    官方源码放哪
#   UNITREE_3H_WS=~/unitree_3h_ws        colcon 工作空间放哪
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPS="${UNITREE_3H_DEPS:-$HOME/unitree_3h_deps}"
WS="${UNITREE_3H_WS:-$HOME/unitree_3h_ws}"
MIRROR="${UNITREE_3H_MIRROR:-auto}"

# 与 README 的 API 表对应的上游版本，固定住，保证人人一致
SDK2PY_SHA=814556d15970dd2ecf1c9984e845ca02ab07e206   # unitree_sdk2_python
ROS2_SHA=668d1ec5a05d1c38d3306bdca7d59f2ba3581a88     # unitree_ros2

step() { printf '\n\033[1;34m==> [%s] %s\033[0m\n' "$1" "$2"; }
retry() { local n=0; until "$@"; do n=$((n+1)); [ "$n" -ge 4 ] && return 1; echo "  重试 $n/3: $*"; sleep 5; done; }

# ---------------------------------------------------------------- 0. 检查
step 0/6 "检查系统"
. /etc/os-release
if [ "${VERSION_ID:-}" != "22.04" ]; then
  echo "本课程只支持 Ubuntu 22.04（当前: ${PRETTY_NAME:-unknown}）"; exit 1
fi
echo "系统: $PRETTY_NAME / $(uname -m)   仓库: $REPO"
case "$REPO" in *" "*) echo "仓库路径里有空格，colcon 会出错。请放到不含空格的路径（例如 ~/unitree-g1-3h）"; exit 1;; esac

if [ "$MIRROR" = auto ]; then
  if curl -fsS -m 8 -o /dev/null https://pypi.org/simple/pip/ 2>/dev/null; then MIRROR=official; else MIRROR=cn; fi
fi
echo "软件源: $MIRROR"
if [ "$MIRROR" = cn ]; then
  ROS_APT=https://mirrors.tuna.tsinghua.edu.cn/ros2/ubuntu
  PIP_ARGS=(-i https://pypi.tuna.tsinghua.edu.cn/simple)
else
  ROS_APT=http://packages.ros.org/ros2/ubuntu
  PIP_ARGS=()
fi

# ---------------------------------------------------------------- 1. 基础工具
step 1/6 "安装基础工具"
export DEBIAN_FRONTEND=noninteractive
retry sudo apt-get update -qq
retry sudo apt-get install -y -qq --no-install-recommends \
  ca-certificates curl gnupg lsb-release git build-essential cmake \
  python3-pip python3-dev iproute2 iputils-ping locales
sudo locale-gen en_US.UTF-8 >/dev/null

# ---------------------------------------------------------------- 2. ROS 2 Humble
step 2/6 "安装 ROS 2 Humble（只装本课需要的）"
KEY=/usr/share/keyrings/ros-archive-keyring.gpg
if [ ! -s "$KEY" ]; then
  retry sudo curl -fsSL -m 60 https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o "$KEY" \
    || retry sudo curl -fsSL -m 60 https://mirrors.tuna.tsinghua.edu.cn/rosdistro/ros.key -o "$KEY"
fi
echo "deb [arch=$(dpkg --print-architecture) signed-by=$KEY] $ROS_APT jammy main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list >/dev/null
retry sudo apt-get update -qq
retry sudo apt-get install -y -qq --no-install-recommends \
  ros-humble-ros-base ros-humble-ros2cli ros-humble-rmw-cyclonedds-cpp \
  ros-humble-rosidl-default-generators ros-humble-rosidl-generator-c \
  ros-humble-rosidl-generator-cpp ros-humble-rosidl-generator-py \
  ros-humble-rosidl-generator-dds-idl ros-humble-sensor-msgs-py \
  python3-colcon-common-extensions python3-matplotlib
sudo apt-get clean

# ---------------------------------------------------------------- 3. Python 依赖
step 3/6 "安装 Python 依赖"
# 不用 pip 装 numpy：ROS 2 Humble 的二进制包按系统 numpy 1.21 编译，升到 2.x 会让 rclpy 报错
retry python3 -m pip install --user -q "${PIP_ARGS[@]}" "cyclonedds==0.10.2"
export PATH="$HOME/.local/bin:$PATH"

# ---------------------------------------------------------------- 4. Unitree 源码
step 4/6 "获取 Unitree 官方源码（固定版本）"
mkdir -p "$DEPS"
fetch_at() {
  local dir="$1" url="$2" ref="$3"
  if [ ! -d "$dir/.git" ]; then retry git clone -q "$url" "$dir"; fi
  if ! git -C "$dir" remote get-url origin >/dev/null 2>&1; then
    git -C "$dir" remote add origin "$url"
  fi
  retry git -C "$dir" fetch -q origin
  git -C "$dir" checkout -q "$ref"
  echo "  $(basename "$dir") @ $(git -C "$dir" rev-parse --short HEAD)"
}
fetch_at "$DEPS/unitree_sdk2_python" https://github.com/unitreerobotics/unitree_sdk2_python.git "$SDK2PY_SHA"
fetch_at "$DEPS/unitree_ros2" https://github.com/unitreerobotics/unitree_ros2.git "$ROS2_SHA"

# unitree_sdk2py 不用 pip 装：它会拉 opencv-python，把 numpy 升到 2.x
USER_SITE="$(python3 -c 'import site; print(site.getusersitepackages())')"
mkdir -p "$USER_SITE"
printf '%s\n' "$DEPS/unitree_sdk2_python" > "$USER_SITE/unitree_3h.pth"

# ---------------------------------------------------------------- 5. 消息工作空间
step 5/6 "编译 Unitree 消息（unitree_go / unitree_hg / unitree_api）"
mkdir -p "$WS/src"
for p in unitree_go unitree_hg unitree_api; do
  ln -sfn "$DEPS/unitree_ros2/cyclonedds_ws/src/unitree/$p" "$WS/src/$p"
done
set +u; source /opt/ros/humble/setup.bash; set -u
( cd "$WS" && colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF )
[ -f "$WS/install/setup.bash" ] || { echo "colcon 编译失败"; exit 1; }

# ---------------------------------------------------------------- 6. 配置与自检
step 6/6 "写入配置并自检"
mkdir -p "$REPO/config"
cat > "$REPO/config/local_paths.env" <<EOF
# 由 scripts/install.sh 生成，勿提交
export UNITREE_3H_DEPS="$DEPS"
export UNITREE_3H_WS="$WS"
EOF

set +u; source "$REPO/scripts/env.sh"; set -u
python3 - <<'EOF'
import cyclonedds, numpy, rclpy
# G1 主线：ROS 2 消息在 unitree_hg，SDK 侧消息在 unitree_sdk2py.idl.unitree_hg
from unitree_hg.msg import LowState
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient
print("  rclpy OK | numpy", numpy.__version__, "| cyclonedds-python OK")
print("  unitree_hg / unitree_sdk2py / G1 LocoClient OK")
EOF
echo
echo "安装完成。之后每开一个新终端先执行："
echo "    source $REPO/scripts/env.sh"
echo "然后连真机："
echo "    python3 scripts/connect.py --iface eth0"
echo "    source scripts/env.sh"
echo "    python3 00_probe.py"
