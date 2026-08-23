"""
股票 L2 Tick 录制器（占位）
- 继承 BaseRecorder，待接入具体 L2 数据源后实现 fields_spec
"""
from core.data_process.base_recorder import BaseRecorder


class StockL2Recorder(BaseRecorder):
    """
    股票 Level2 Tick 录制器（占位）

    未来实现要点：
    - fields_spec 扩展十档买卖盘字段
    - 落盘路径: data/raw/stock/level2/tick/
    - bin 格式待定义（含十档买卖价量、委托队列等）
    """

    # 占位：先用与期货相同的公共字段，待实现时扩展
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

    def __init__(self, tick_queue, data_dir="data/raw/stock/level2/tick",
                 max_records_per_file=500000, zmq_bind_url="tcp://*:5555", zmq_publisher=None):
        super().__init__(
            tick_queue=tick_queue,
            asset_type="stock",
            data_dir=data_dir,
            fields_spec=self.FIELDS_SPEC,
            max_records_per_file=max_records_per_file,
            zmq_bind_url=zmq_bind_url,
            zmq_publisher=zmq_publisher
        )

    def _extract_pack_values(self, tick_obj) -> tuple:
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

    def _extract_redis_snapshot(self, tick_obj, M: float) -> dict:
        return {
            "trade_date": tick_obj.trade_date,
            "update_time": f"{tick_obj.update_time:06d}.{tick_obj.update_millisec:03d}",
            "last_price": tick_obj.last_price / M,
            "volume": tick_obj.volume,
        }
