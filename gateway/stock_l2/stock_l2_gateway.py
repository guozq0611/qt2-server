"""
股票 Level2 行情网关（占位）
- 未来接入沪深交易所直连或第三方 L2 数据源时实现
- 继承 BaseMdGateway，实现 connect/subscribe/release
"""
from core.gateway.base_gateway import BaseMdGateway


class StockL2Gateway(BaseMdGateway):
    """
    股票 Level2 行情网关（占位）

    未来实现要点：
    - 数据源：沪深交易所直连 / 第三方 L2 数据源（如华宝、腾讯等）
    - 协议：可能基于 TCP/UDP 组播或 WebSocket
    - 回调：解析 L2 数据后构造 StockL2TickData 推入 tick_queue
    - 十档买卖盘、逐笔委托/成交
    """

    def connect(self):
        raise NotImplementedError("StockL2Gateway 尚未实现，等待接入具体 L2 数据源")

    def subscribe(self, symbols):
        raise NotImplementedError("StockL2Gateway 尚未实现")

    def release(self):
        pass
