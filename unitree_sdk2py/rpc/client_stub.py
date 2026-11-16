# =============================================================================
# 课程阅读副本 · 官方源码，逻辑未改动，只加了注释
# 上游: https://github.com/unitreerobotics/unitree_sdk2_python
# 版本: 814556d15970dd2ecf1c9984e845ca02ab07e206（与 scripts/install.sh 固定的一致）
# 本文件: unitree_sdk2py/rpc/client_stub.py
# 课程位置: 02_actions.py（调用链底层）
#
# ▶ 真正碰 DDS 的地方：
#   发送通道 rt/api/<service>/request，接收通道 rt/api/<service>/response。
#   response 回调按 identity.id 找到对应的 future 并置结果 ——
#   这就是“同步 RPC”背后的异步转同步。
#   Init() 里的 time.sleep(0.5) 是在等 DDS 发现（discovery）完成；
#   删掉它，程序刚启动时的第一条请求经常直接丢掉。
# =============================================================================
import time

from enum import Enum
from threading import Thread, Condition

from ..idl.unitree_api.msg.dds_ import Request_ as Request
from ..idl.unitree_api.msg.dds_ import Response_ as Response

from ..core.channel import ChannelFactory
from ..core.channel_name import ChannelType, GetClientChannelName
from .request_future import RequestFuture, RequestFutureQueue


"""
" class ClientStub
"""
class ClientStub:
    def __init__(self, serviceName: str):
        self.__serviceName = serviceName
        self.__futureQueue = None

        self.__sendChannel = None
        self.__recvChannel = None

    def Init(self):
        factory = ChannelFactory()
        self.__futureQueue = RequestFutureQueue()

        # create channel
        self.__sendChannel = factory.CreateSendChannel(GetClientChannelName(self.__serviceName, ChannelType.SEND), Request)
        self.__recvChannel = factory.CreateRecvChannel(GetClientChannelName(self.__serviceName, ChannelType.RECV), Response,
                                    self.__ResponseHandler,10)
        time.sleep(0.5)


    def Send(self, request: Request, timeout: float):
        if self.__sendChannel.Write(request, timeout):
            return True
        else:
            print("[ClientStub] send error. id:", request.header.identity.id)
            return False

    def SendRequest(self, request: Request, timeout: float):
        id = request.header.identity.id

        future = RequestFuture()
        future.SetRequestId(id)
        self.__futureQueue.Set(id, future)

        if self.__sendChannel.Write(request, timeout):
            return future
        else:
            print("[ClientStub] send request error. id:", request.header.identity.id)
            self.__futureQueue.Remove(id)
            return None

    def RemoveFuture(self, requestId: int):
        self.__futureQueue.Remove(requestId)

    def __ResponseHandler(self, response: Response):
        id = response.header.identity.id
        # apiId = response.header.identity.api_id
        # print("[ClientStub] responseHandler recv response id:", id, ", apiId:", apiId)
        future = self.__futureQueue.Get(id)
        if future is None:
            # print("[ClientStub] get future from queue error. id:", id)
            pass
        elif not future.Ready(response):
            print("[ClientStub] set future ready error.")
