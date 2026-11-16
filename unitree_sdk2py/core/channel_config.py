# =============================================================================
# 课程阅读副本 · 官方源码，逻辑未改动，只加了注释
# 上游: https://github.com/unitreerobotics/unitree_sdk2_python
# 版本: 814556d15970dd2ecf1c9984e845ca02ab07e206（与 scripts/install.sh 固定的一致）
# 本文件: unitree_sdk2py/core/channel_config.py
# 课程位置: scripts/connect.py（生成的 config/cyclonedds.xml）
#
# ▶ 这里就是 CYCLONEDDS_URI 里那段 XML 的模板。
#   ChannelFactoryInitialize(0, "eth0") 时，$__IF_NAME__$ 会被替换成网卡名。
#   传 None 时用 autodetermine=true，让 CycloneDDS 自己挑网卡 ——
#   多网卡机器（有线 + Wi-Fi + 虚拟机网桥）上经常挑错，于是“收不到数据”。
#   scripts/connect.py 生成的 config/cyclonedds.xml 本质就是这份配置。
# =============================================================================
ChannelConfigHasInterface = '''<?xml version="1.0" encoding="UTF-8" ?>
    <CycloneDDS>
        <Domain Id="any">
            <General>
                <Interfaces>
                    <NetworkInterface name="$__IF_NAME__$" priority="default" multicast="default"/>
                </Interfaces>
            </General>
            <Tracing>
                <Verbosity>config</Verbosity>
            <OutputFile>/tmp/cdds.LOG</OutputFile>
        </Tracing>
        </Domain>
    </CycloneDDS>'''

ChannelConfigAutoDetermine = '''<?xml version="1.0" encoding="UTF-8" ?>
    <CycloneDDS>
        <Domain Id="any">
            <General>
                <Interfaces>
                    <NetworkInterface autodetermine=\"true\" priority=\"default\" multicast=\"default\" />
                </Interfaces>
            </General>
        </Domain>
    </CycloneDDS>'''
