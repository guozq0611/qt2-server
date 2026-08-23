"""
股票 Level2 Tick 数据（占位）
- 继承 BaseTick，扩展股票 L2 专用字段
- 未来接入沪深交易所直连或第三方 L2 数据源时实现
"""
from dataclasses import dataclass
from core.entity.base_tick import BaseTick


@dataclass(slots=True)
class StockL2TickData(BaseTick):
    """
    股票 Level2 Tick 数据（占位）
    扩展字段待接入具体数据源后补充：
    - 十档买卖盘（CTP 只有 1 档，L2 通常有 10 档）
    - 逐笔委托/成交
    - 委托买卖队列
    """
    # --- 股票 L2 专属字段（占位，待实现） ---
    # bid_price_2 ~ bid_price_10: int = 0
    # bid_volume_2 ~ bid_volume_10: int = 0
    # ask_price_2 ~ ask_price_10: int = 0
    # ask_volume_2 ~ ask_volume_10: int = 0
    # num_orders_bid: int = 0    # 买侧委托队列数量
    # num_orders_ask: int = 0    # 卖侧委托队列数量
    pass
