"""
股票期权 Tick 录制器
- 继承 BaseRecorder，定义股票期权的 fields_spec
- bin 格式在期权基础上扩展 5 档买卖盘（2-5 档）
- 股票期权走 CTP 股票期权柜台（openctp_ctpopt），推送 5 档买卖盘
"""
from core.data_process.base_recorder import BaseRecorder
from core.entity.stock_option_tick import StockOptionLevel1TickData


class StockOptionTickRecorder(BaseRecorder):
    """
    股票期权 Level1 Tick 录制器

    bin 格式（在期权基础上扩展 5 档买卖盘，合计 362 字节/条）：
    - 公共字段（同期货，instrument_id 扩展为 20s）
    - 期权专属字段（同期权）
    - 5 档买卖盘 2-5 档（8 个 price + 8 个 volume = 16 个 q = 128 字节）
    - 注意：1 档已在公共字段中
    """

    TICK_CLASS = StockOptionLevel1TickData

    FIELDS_SPEC = [
        # --- 公共字段（同期货，instrument_id 扩展为 20s 以容纳股票期权长代码） ---
        ('instrument_id',      '20s'),
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
        # --- 5 档买卖盘 2-5 档 ---
        ('bid_price_2',         'q'),
        ('bid_volume_2',        'q'),
        ('bid_price_3',         'q'),
        ('bid_volume_3',        'q'),
        ('bid_price_4',         'q'),
        ('bid_volume_4',        'q'),
        ('bid_price_5',         'q'),
        ('bid_volume_5',        'q'),
        ('ask_price_2',         'q'),
        ('ask_volume_2',        'q'),
        ('ask_price_3',         'q'),
        ('ask_volume_3',        'q'),
        ('ask_price_4',         'q'),
        ('ask_volume_4',        'q'),
        ('ask_price_5',         'q'),
        ('ask_volume_5',        'q'),
    ]

    def __init__(self, tick_queue, data_dir="data/raw/stock_option/level1/tick",
                 max_records_per_file=500000, zmq_bind_url="tcp://*:5555", zmq_publisher=None):
        super().__init__(
            tick_queue=tick_queue,
            asset_type="stock_option",
            data_dir=data_dir,
            fields_spec=self.FIELDS_SPEC,
            max_records_per_file=max_records_per_file,
            zmq_bind_url=zmq_bind_url,
            zmq_publisher=zmq_publisher
        )

    def _extract_pack_values(self, tick_obj: StockOptionLevel1TickData) -> tuple:
        return (
            tick_obj.instrument_id.encode('utf-8')[:20],
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
            # 5 档买卖盘 2-5 档
            tick_obj.bid_price_2,
            tick_obj.bid_volume_2,
            tick_obj.bid_price_3,
            tick_obj.bid_volume_3,
            tick_obj.bid_price_4,
            tick_obj.bid_volume_4,
            tick_obj.bid_price_5,
            tick_obj.bid_volume_5,
            tick_obj.ask_price_2,
            tick_obj.ask_volume_2,
            tick_obj.ask_price_3,
            tick_obj.ask_volume_3,
            tick_obj.ask_price_4,
            tick_obj.ask_volume_4,
            tick_obj.ask_price_5,
            tick_obj.ask_volume_5,
        )

    def _extract_redis_snapshot(self, tick_obj: StockOptionLevel1TickData, M: float) -> dict:
        return {
            "trade_date": tick_obj.trade_date,
            "update_time": f"{tick_obj.update_time:06d}.{tick_obj.update_millisec:03d}",
            "last_price": tick_obj.last_price / M,
            "volume": tick_obj.volume,
            "open_interest": tick_obj.open_interest,
            "bid_price_1": tick_obj.bid_price_1 / M,
            "bid_volume_1": tick_obj.bid_volume_1,
            "ask_price_1": tick_obj.ask_price_1 / M,
            "ask_volume_1": tick_obj.ask_volume_1,
            "bid_price_2": tick_obj.bid_price_2 / M,
            "bid_volume_2": tick_obj.bid_volume_2,
            "ask_price_2": tick_obj.ask_price_2 / M,
            "ask_volume_2": tick_obj.ask_volume_2,
            "bid_price_3": tick_obj.bid_price_3 / M,
            "bid_volume_3": tick_obj.bid_volume_3,
            "ask_price_3": tick_obj.ask_price_3 / M,
            "ask_volume_3": tick_obj.ask_volume_3,
            "bid_price_4": tick_obj.bid_price_4 / M,
            "bid_volume_4": tick_obj.bid_volume_4,
            "ask_price_4": tick_obj.ask_price_4 / M,
            "ask_volume_4": tick_obj.ask_volume_4,
            "bid_price_5": tick_obj.bid_price_5 / M,
            "bid_volume_5": tick_obj.bid_volume_5,
            "ask_price_5": tick_obj.ask_price_5 / M,
            "ask_volume_5": tick_obj.ask_volume_5,
            "underlying": tick_obj.underlying_symbol,
            "strike": tick_obj.strike_price / M,
            "type": tick_obj.contract_type,
            "exchange": tick_obj.exchange_id,
            "delta": tick_obj.delta,
            "implied_vol": tick_obj.implied_vol,
        }
