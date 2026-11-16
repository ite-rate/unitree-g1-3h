# =============================================================================
# 课程阅读副本 · 官方源码，逻辑未改动，只加了注释
# 上游: https://github.com/unitreerobotics/unitree_sdk2_python
# 版本: 814556d15970dd2ecf1c9984e845ca02ab07e206（与 scripts/install.sh 固定的一致）
# 本文件: unitree_sdk2py/rpc/internal.py
# 课程位置: README 排障表 / 全部课程脚本
#
# ▶ 错误码总表，课堂排障直接对照：
#   0     成功
#   3102  发送失败（DDS 没连上、网卡选错）
#   3103  API 没注册（自己乱写 ID，或客户端版本太旧）
#   3104  等回复超时（机器人没响应、被 App/遥控器接管）
#   3105  回复的 api_id 对不上（请求/响应串了）
#   3203  服务端没实现（固件不支持这个动作）
#   3204  参数错（JSON 字段名/类型写错）
# =============================================================================
# internal api id max
RPC_INTERNAL_API_ID_MAX = 100

# internal api id
RPC_API_ID_INTERNAL_API_VERSION  = 1

# lease api id
RPC_API_ID_LEASE_APPLY = 101
RPC_API_ID_LEASE_RENEWAL = 102

# lease term default
RPC_LEASE_TERM = 1.0

# internal error
RPC_OK = 0
# client error
RPC_ERR_UNKNOWN = 3001
RPC_ERR_CLIENT_SEND = 3102
RPC_ERR_CLIENT_API_NOT_REG = 3103
RPC_ERR_CLIENT_API_TIMEOUT = 3104
RPC_ERR_CLIENT_API_NOT_MATCH = 3105
RPC_ERR_CLIENT_API_DATA = 3106
RPC_ERR_CLIENT_LEASE_INVALID = 3107
# server error
RPC_ERR_SERVER_SEND = 3201
RPC_ERR_SERVER_INTERNAL = 3202
RPC_ERR_SERVER_API_NOT_IMPL = 3203
RPC_ERR_SERVER_API_PARAMETER = 3204
RPC_ERR_SERVER_LEASE_DENIED = 3205
RPC_ERR_SERVER_LEASE_NOT_EXIST = 3206
RPC_ERR_SERVER_LEASE_EXIST = 3207
