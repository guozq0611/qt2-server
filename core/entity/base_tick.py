"""
Tick 数据抽象基类
- 定义所有资产类型 tick 的公共字段和行为
- 具体资产类型（期货/期权/股票/数字货币）继承此类扩展各自字段
"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass(slots=True)
class BaseTick:
    """
    所有 tick 数据的公共基类
    注意：为对齐 ClickHouse 的 Int64，价格和金额字段在外部实例化时应已放大至整数。
    """
    # --- 标识 ---
    instrument_id: str           # 合约代码, 例: 'IF2309' / 'IO2603-C-4200' / '000001'
    exchange_id: str             # 交易所代码, 例: 'CFFEX' / 'SSE' / 'BINANCE'

    # --- 时间 ---
    trade_date: int              # 交易日, 例: 20230915
    action_date: int             # 实际交易日, 例: 20230915
    update_time: int             # 时间戳整型, 例: 145700
    update_millisec: int         # 毫秒, 例: 100
    local_time_ns: int           # 本地机器接收到网络包的纳秒时间戳

    # --- 量价（公共字段） ---
    last_price: int              # 最新价（已放大 10000 倍）
    volume: int                  # 累计成交量
    turnover: int                # 累计成交金额
    open_interest: int           # 持仓量

    # --- 盘口一档（公共字段） ---
    bid_price_1: int             # 买一价
    bid_volume_1: int            # 买一量
    ask_price_1: int             # 卖一价
    ask_volume_1: int            # 卖一量

    # --- 日内极值与参考价 ---
    open_price: int              # 今开盘
    highest_price: int           # 最高价
    lowest_price: int            # 最低价
    average_price: int           # 日内均价
    upper_limit_price: int       # 涨停板价
    lower_limit_price: int       # 跌停板价

    # --- 隐藏缓存 ---
    _datetime_cache: Optional[datetime] = field(default=None, init=False, repr=False)

    @property
    def unique_symbol(self) -> str:
        return f"{self.instrument_id}.{self.exchange_id}"

    @property
    def dt_obj(self) -> datetime:
        """懒加载获取真实的 datetime 对象"""
        if self._datetime_cache is None:
            time_str = str(self.update_time).zfill(6)
            hours = int(time_str[:2])
            minutes = int(time_str[2:4])
            seconds = int(time_str[4:6])

            date_str = str(self.action_date)
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])

            self._datetime_cache = datetime(
                year=year, month=month, day=day,
                hour=hours, minute=minutes, second=seconds,
                microsecond=self.update_millisec * 1000
            )
        return self._datetime_cache

    @property
    def mid_price(self) -> float:
        """盘口中间价"""
        if self.bid_volume_1 > 0 and self.ask_volume_1 > 0:
            return (self.bid_price_1 + self.ask_price_1) / 2.0
        return float(self.last_price)
