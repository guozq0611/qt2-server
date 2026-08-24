"""
行情网关抽象基类
- 定义所有行情网关的统一接口
- 具体网关（CTP/股票L2/数字货币）继承此类实现各自的数据源接入
"""
from abc import ABC, abstractmethod
import queue
from typing import List


class BaseMdGateway(ABC):
    """
    行情网关抽象基类

    职责：仅负责连接数据源、登录、订阅、解析原生数据，并推入内存队列。
    不负责落盘、广播、监控等下游逻辑。

    子类需要实现：
    - connect(): 发起连接
    - subscribe(symbols): 订阅合约
    - release(): 安全释放连接
    """

    def __init__(self, config: dict, tick_queue: queue.Queue):
        self.config = config
        self.tick_queue = tick_queue
        self.is_connected = False
        self.is_logged_in = False
        self.subscribed_symbols = set()

    @abstractmethod
    def connect(self):
        """发起连接"""
        ...

    @abstractmethod
    def subscribe(self, symbols: List[str]):
        """订阅合约列表"""
        ...

    @abstractmethod
    def release(self):
        """安全释放连接"""
        ...
