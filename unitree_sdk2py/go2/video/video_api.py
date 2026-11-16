# =============================================================================
# 课程阅读副本 · 官方源码，逻辑未改动，只加了注释
# 上游: https://github.com/unitreerobotics/unitree_sdk2_python
# 版本: 814556d15970dd2ecf1c9984e845ca02ab07e206（与 scripts/install.sh 固定的一致）
# 本文件: unitree_sdk2py/go2/video/video_api.py
# 课程位置: 05_camera.py / 07_demo_show.py
#
# ▶ 相机服务名是 videohub，不是 video；只有 1001 一个接口 GetImageSample。
# =============================================================================
"""
" service name
"""
VIDEO_SERVICE_NAME = "videohub"


"""
" service api version
"""
VIDEO_API_VERSION = "1.0.0.1"


"""
" api id
"""
VIDEO_API_ID_GETIMAGESAMPLE = 1001
