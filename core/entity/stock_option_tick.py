"""
股票期权 Level1 Tick 数据
- 继承 OptionLevel1TickData，扩展 5 档买卖盘
- 股票期权（ETF 期权）走 CTP 股票期权柜台（openctp_ctpopt）
- 与期货期权的差异：CTP 股票期权柜台推送 5 档买卖盘（BidPrice1-5 / AskPrice1-5）
"""
from dataclasses import dataclass
from core.entity.option_tick import OptionLevel1TickData


@dataclass(slots=True)
class StockOptionLevel1TickData(OptionLevel1TickData):
    """
    股票期权 Level1 Tick 数据
    在期权基础上扩展 5 档买卖盘（CTP 股票期权柜台推送 5 档）。
    """
    # --- 2-5 档买卖盘（CTP 股票期权柜台推送，期货期权只有 1 档） ---
    bid_price_2: int = 0
    bid_volume_2: int = 0
    bid_price_3: int = 0
    bid_volume_3: int = 0
    bid_price_4: int = 0
    bid_volume_4: int = 0
    bid_price_5: int = 0
    bid_volume_5: int = 0

    ask_price_2: int = 0
    ask_volume_2: int = 0
    ask_price_3: int = 0
    ask_volume_3: int = 0
    ask_price_4: int = 0
    ask_volume_4: int = 0
    ask_price_5: int = 0
    ask_volume_5: int = 0
