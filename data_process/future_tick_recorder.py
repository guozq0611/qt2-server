"""
期货 Tick 录制器
- 从原 quantlab/core/data_process/bin_future_tick_recorder.py 迁移
- 继承 BaseRecorder，定义期货的 fields_spec 和字段提取逻辑
- bin 格式与原版完全对齐（160 字节/条），下游 ClickHouse 消费链路无感知
"""
from core.data_process.base_recorder import BaseRecorder
from core.entity.future_tick import FutureLevel1TickData


class FutureTickRecorder(BaseRecorder):
    """
    期货 Level1 Tick 录制器

    bin 格式（160 字节/条，小端序）：
    - instrument_id:      16s (字符串)
    - exchange_id:         8s (字符串)
    - trade_date:          i  (4字节整型)
    - action_date:         i
    - update_time:         i
    - update_millisec:     i
    - local_time_ns:       q  (8字节整型)
    - last_price:          q
    - volume:              q
    - turnover:            q
    - open_interest:       q
    - bid_price_1:         q
    - bid_volume_1:        q
    - ask_price_1:         q
    - ask_volume_1:        q
    - open_price:          q
    - highest_price:       q
    - lowest_price:        q
    - average_price:       q
    - upper_limit_price:   q
    - lower_limit_price:   q
    """

    TICK_CLASS = FutureLevel1TickData

    FIELDS_SPEC = [
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
    ]

    def __init__(self, tick_queue, data_dir="data/raw/future/level1/tick",
                 max_records_per_file=500000, zmq_bind_url="tcp://*:5555", zmq_publisher=None):
        super().__init__(
            tick_queue=tick_queue,
            asset_type="future",
            data_dir=data_dir,
            fields_spec=self.FIELDS_SPEC,
            max_records_per_file=max_records_per_file,
            zmq_bind_url=zmq_bind_url,
            zmq_publisher=zmq_publisher
        )

    def _extract_pack_values(self, tick_obj: FutureLevel1TickData) -> tuple:
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
        )

    def _extract_redis_snapshot(self, tick_obj: FutureLevel1TickData, M: float) -> dict:
        return {
            "trade_date": tick_obj.trade_date,
            "update_time": f"{tick_obj.update_time:06d}.{tick_obj.update_millisec:03d}",
            "last_price": tick_obj.last_price / M,
            "volume": tick_obj.volume,
            "turnover": tick_obj.turnover,
            "open_interest": tick_obj.open_interest,
            "bid_price_1": tick_obj.bid_price_1 / M,
            "bid_volume_1": tick_obj.bid_volume_1,
            "ask_price_1": tick_obj.ask_price_1 / M,
            "ask_volume_1": tick_obj.ask_volume_1,
        }
