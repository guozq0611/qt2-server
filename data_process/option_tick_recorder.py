"""
期权 Tick 录制器
- 继承 BaseRecorder，定义期权的 fields_spec
- bin 格式在期货基础上扩展期权专属字段
- 注意：Greeks 字段 CTP 不推送，默认 0，下游计算后可覆盖
"""
from core.data_process.base_recorder import BaseRecorder
from core.entity.option_tick import OptionLevel1TickData


class OptionTickRecorder(BaseRecorder):
    """
    期权 Level1 Tick 录制器

    bin 格式（在期货 160 字节基础上扩展，合计 230 字节/条）：
    - 公共字段（同期货，160 字节）
    - underlying_symbol:   16s
    - strike_price:         q
    - contract_type:        2s  ('C' / 'P')
    - expiry_date:          i
    - delta:                d  (8字节 double)
    - gamma:                d
    - vega:                 d
    - theta:                d
    - implied_vol:          d
    """

    FIELDS_SPEC = [
        # --- 公共字段（同期货） ---
        ('instrument_id',      '16s'),
        ('exchange_id',         '8s'),
        ('trade_date',          'i'),
        ('action_date',         'i'),
        ('update_time',         'i'),
        ('update_millisec',     'i'),
        ('local_time_ns',       'q'),
        ('last_price',          'q'),
        ('volume',              'q'),
        ('turnover',            'q'),
        ('open_interest',       'q'),
        ('bid_price_1',         'q'),
        ('bid_volume_1',        'q'),
        ('ask_price_1',         'q'),
        ('ask_volume_1',        'q'),
        ('open_price',          'q'),
        ('highest_price',       'q'),
        ('lowest_price',        'q'),
        ('average_price',       'q'),
        ('upper_limit_price',   'q'),
        ('lower_limit_price',   'q'),
        # --- 期权专属字段 ---
        ('underlying_symbol',  '16s'),
        ('strike_price',        'q'),
        ('contract_type',       '2s'),
        ('expiry_date',         'i'),
        ('delta',               'd'),
        ('gamma',               'd'),
        ('vega',                'd'),
        ('theta',               'd'),
        ('implied_vol',         'd'),
    ]

    def __init__(self, tick_queue, data_dir="data/raw/option/level1/tick",
                 max_records_per_file=500000, zmq_bind_url="tcp://*:5555", zmq_publisher=None):
        super().__init__(
            tick_queue=tick_queue,
            asset_type="option",
            data_dir=data_dir,
            fields_spec=self.FIELDS_SPEC,
            max_records_per_file=max_records_per_file,
            zmq_bind_url=zmq_bind_url,
            zmq_publisher=zmq_publisher
        )

    def _extract_pack_values(self, tick_obj: OptionLevel1TickData) -> tuple:
        return (
            tick_obj.instrument_id.encode('utf-8')[:16],
            tick_obj.exchange_id.encode('utf-8')[:8],
            tick_obj.trade_date,
            tick_obj.action_date,
            tick_obj.update_time,
            tick_obj.update_millisec,
            tick_obj.local_time_ns,
            tick_obj.last_price,
            tick_obj.volume,
            tick_obj.turnover,
            tick_obj.open_interest,
            tick_obj.bid_price_1,
            tick_obj.bid_volume_1,
            tick_obj.ask_price_1,
            tick_obj.ask_volume_1,
            tick_obj.open_price,
            tick_obj.highest_price,
            tick_obj.lowest_price,
            tick_obj.average_price,
            tick_obj.upper_limit_price,
            tick_obj.lower_limit_price,
            # 期权专属
            tick_obj.underlying_symbol.encode('utf-8')[:16],
            tick_obj.strike_price,
            tick_obj.contract_type.encode('utf-8')[:2],
            tick_obj.expiry_date,
            tick_obj.delta,
            tick_obj.gamma,
            tick_obj.vega,
            tick_obj.theta,
            tick_obj.implied_vol,
        )

    def _extract_redis_snapshot(self, tick_obj: OptionLevel1TickData, M: float) -> dict:
        return {
            "trade_date": tick_obj.trade_date,
            "update_time": f"{tick_obj.update_time:06d}.{tick_obj.update_millisec:03d}",
            "last_price": tick_obj.last_price / M,
            "volume": tick_obj.volume,
            "open_interest": tick_obj.open_interest,
            "bid_price_1": tick_obj.bid_price_1 / M,
            "ask_price_1": tick_obj.ask_price_1 / M,
            "underlying": tick_obj.underlying_symbol,
            "strike": tick_obj.strike_price / M,
            "type": tick_obj.contract_type,
            "delta": tick_obj.delta,
            "implied_vol": tick_obj.implied_vol,
        }
