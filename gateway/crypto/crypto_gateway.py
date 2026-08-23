"""
数字货币行情网关（占位）
- 未来接入 Binance/OKX 等交易所 WebSocket 时实现
- 继承 BaseMdGateway，实现 connect/subscribe/release
"""
from core.gateway.base_gateway import BaseMdGateway


class CryptoGateway(BaseMdGateway):
    """
    数字货币行情网关（占位）

    未来实现要点：
    - 数据源：Binance / OKX / Bybit 等交易所 WebSocket API
    - 协议：WSS（WebSocket Secure）
    - 回调：解析 ticker/stream 数据后构造 CryptoTickData 推入 tick_queue
    - 多档深度（通常 20 档）、资金费率（永续合约）
    """

    def connect(self):
        raise NotImplementedError("CryptoGateway 尚未实现，等待接入具体交易所 WebSocket")

    def subscribe(self, symbols):
        raise NotImplementedError("CryptoGateway 尚未实现")

    def release(self):
        pass
