"""
CTP 行情网关
- 从原 quantlab/core/gateway/ctp/ctp_md_gateway.py 迁移
- 改为继承 BaseMdGateway（同时保留继承 mdapi.CThostFtdcMdSpi 用于 C++ 回调）
- 支持期货 + 期权行情接收（CTP 同一连接即可）
"""
import os
import queue
import logging
import time
from typing import List

# 优先使用 openctp_ctp PyPI 包；如不可用可切换到本地 ctp_lib
# from .ctp_lib import thostmduserapi as mdapi
from openctp_ctp import thostmduserapi as mdapi

from core.entity.future_tick import FutureLevel1TickData
from core.entity.option_tick import OptionLevel1TickData
from core.gateway.base_gateway import BaseMdGateway


class CtpMdGateway(BaseMdGateway, mdapi.CThostFtdcMdSpi):
    """
    CTP 行情网关 (Market Data Gateway)
    职责：仅负责连接柜台、登录、订阅、解析原生数据，并推入内存队列。
    支持期货 + 期权行情（CTP 同一连接，订阅时传入对应合约代码即可）。
    """
    def __init__(self, config: dict, tick_queue: queue.Queue):
        # 显式初始化两个父类
        BaseMdGateway.__init__(self, config, tick_queue)
        mdapi.CThostFtdcMdSpi.__init__(self)

        self.symbol_exchange_map = self.config.get("symbol_exchange_map", {})
        # 资产类型映射：instrument_id -> 'FUTURE' / 'OPTION'
        # 用于区分回调中收到的 tick 应该构造成 FutureLevel1TickData 还是 OptionLevel1TickData
        self.symbol_asset_type_map = self.config.get("symbol_asset_type_map", {})

    def connect(self):
        """外部调用：发起连接"""
        front_addr = self.config.get("front_address")
        if not front_addr:
            logging.error("CTP行情网关启动失败: 缺少 front_address 配置")
            return

        logging.info(f"CTP行情网关正在连接前置机: {front_addr}")

        os.makedirs("logs", exist_ok=True)
        self.api = mdapi.CThostFtdcMdApi.CreateFtdcMdApi("logs/ctp_md_")
        self.api.RegisterFront(front_addr)
        self.api.RegisterSpi(self)

        # CTP 的 Init() 是异步非阻塞的，底层会启动独立线程
        self.api.Init()

    def release(self):
        """外部调用：安全释放连接"""
        if hasattr(self, 'api') and self.api:
            self.api.RegisterSpi(None)
            self.api.Release()
            self.api = None
            logging.info("CTP行情网关已安全释放")

    # ==========================================================
    # 以下为 CTP 原生回调函数 (C++ Override)
    # ==========================================================

    def OnFrontConnected(self) -> "void":
        """回调：前置机连接成功"""
        self.is_connected = True
        logging.info("CTP行情前置机连接成功！正在发起登录...")

        req = mdapi.CThostFtdcReqUserLoginField()
        self.api.ReqUserLogin(req, 0)

    def OnFrontDisconnected(self, nReason: int) -> "void":
        """回调：前置机断开"""
        self.is_connected = False
        self.is_logged_in = False
        logging.warning(f"CTP行情前置机断开连接，原因代码: {nReason}")

    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast) -> "void":
        """回调：登录回执"""
        if pRspInfo is not None and pRspInfo.ErrorID != 0:
            logging.error(f"行情登录失败: {pRspInfo.ErrorMsg}")
            return

        self.is_logged_in = True
        trading_day = self.api.GetTradingDay()
        logging.info(f"CTP行情登录成功! 当前交易日: {trading_day}")

        # 登录成功后，自动订阅配置中的合约 (支持断线重连后的自动恢复)
        symbols_to_sub = self.config.get("subscribe_list", [])
        if self.subscribed_symbols:
            symbols_to_sub = list(self.subscribed_symbols)

        if symbols_to_sub:
            self.subscribe(symbols_to_sub)

    def subscribe(self, symbols: List[str]):
        """执行订阅动作"""
        if not self.is_logged_in:
            logging.warning("尚未登录，合约加入待订阅队列")
            self.subscribed_symbols.update(symbols)
            return

        # 原生 CTP 接口要求传入 bytes 列表
        bytes_list = [s.encode('utf-8') for s in symbols]
        self.api.SubscribeMarketData(bytes_list, len(bytes_list))
        self.subscribed_symbols.update(symbols)
        logging.info(f"发送订阅请求，合约数量: {len(symbols)}")

    def OnRtnDepthMarketData(self, pDepthMarketData) -> "void":
        """
        回调：核心行情推送 (Tick 数据到达)
        根据合约的资产类型，构造 FutureLevel1TickData 或 OptionLevel1TickData
        """
        if not pDepthMarketData or not pDepthMarketData.InstrumentID:
            return

        # 1. 时间字段极速整型化 (过滤掉 CTP 偶尔传回的空值导致的崩溃)
        try:
            trade_date_val = int(pDepthMarketData.TradingDay) if pDepthMarketData.TradingDay else 0
        except ValueError:
            trade_date_val = 0

        try:
            action_date_val = int(pDepthMarketData.ActionDay) if pDepthMarketData.ActionDay else 0
        except ValueError:
            action_date_val = 0

        try:
            time_str = pDepthMarketData.UpdateTime
            update_time_val = int(time_str.replace(':', '')) if time_str else 0
        except Exception:
            update_time_val = 0

        # 2. 定义乘数 (对齐底层 UInt64/Int64 需求)
        M = 10000

        instrument_id = pDepthMarketData.InstrumentID

        # 兼容处理：如果是 bytes 就解码为 str
        if isinstance(instrument_id, bytes):
            instrument_id = instrument_id.decode('gbk')

        # 3. 公共字段（期货和期权共享）
        common_fields = dict(
            instrument_id=pDepthMarketData.InstrumentID,
            exchange_id=self.symbol_exchange_map.get(pDepthMarketData.InstrumentID, ""),

            trade_date=trade_date_val,
            action_date=action_date_val,
            update_time=update_time_val,
            update_millisec=int(pDepthMarketData.UpdateMillisec),
            local_time_ns=time.time_ns(),

            last_price=0 if pDepthMarketData.LastPrice > 1e30 else int(pDepthMarketData.LastPrice * M),
            volume=int(pDepthMarketData.Volume),
            turnover=0 if pDepthMarketData.Turnover > 1e30 else int(pDepthMarketData.Turnover * 100),
            open_interest=int(pDepthMarketData.OpenInterest),

            bid_price_1=0 if pDepthMarketData.BidPrice1 > 1e30 else int(pDepthMarketData.BidPrice1 * M),
            bid_volume_1=int(pDepthMarketData.BidVolume1),
            ask_price_1=0 if pDepthMarketData.AskPrice1 > 1e30 else int(pDepthMarketData.AskPrice1 * M),
            ask_volume_1=int(pDepthMarketData.AskVolume1),

            open_price=0 if pDepthMarketData.OpenPrice > 1e30 else int(pDepthMarketData.OpenPrice * M),
            highest_price=0 if pDepthMarketData.HighestPrice > 1e30 else int(pDepthMarketData.HighestPrice * M),
            lowest_price=0 if pDepthMarketData.LowestPrice > 1e30 else int(pDepthMarketData.LowestPrice * M),
            average_price=0 if pDepthMarketData.AveragePrice > 1e30 else int(pDepthMarketData.AveragePrice * M),
            upper_limit_price=0 if pDepthMarketData.UpperLimitPrice > 1e30 else int(pDepthMarketData.UpperLimitPrice * M),
            lower_limit_price=0 if pDepthMarketData.LowerLimitPrice > 1e30 else int(pDepthMarketData.LowerLimitPrice * M),
        )

        # 4. 根据资产类型构造对应的 tick 对象
        asset_type = self.symbol_asset_type_map.get(instrument_id, 'FUTURE')

        if asset_type == 'OPTION':
            tick_obj = OptionLevel1TickData(**common_fields)
            # 期权专属字段：CTP 行情不推送 Greeks，这里留默认值
            # underlying_symbol / strike_price / contract_type / expiry_date
            # 由下游从 option_info 表查询后填充
        else:
            tick_obj = FutureLevel1TickData(**common_fields)

        # 推入内存队列，网关的职责到此完美结束
        self.tick_queue.put(tick_obj)
