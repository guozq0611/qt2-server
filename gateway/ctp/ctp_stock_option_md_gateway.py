"""
CTP 股票期权行情网关
- 使用 openctp_ctpopt（CTP 股票期权 API，与期货 API 接口结构一致但底层库不同）
- 接收股票 ETF 期权行情（SSE/SZSE），推送 5 档买卖盘
- 行情前置不验证密码，空登录即可（与期货 md 一致）
"""
import os
import queue
import logging
import time
from typing import List

from openctp_ctpopt import soptthostmduserapi as mdapi

from core.entity.stock_option_tick import StockOptionLevel1TickData
from core.gateway.base_gateway import BaseMdGateway


class CtpStockOptionMdGateway(BaseMdGateway, mdapi.CThostFtdcMdSpi):
    """
    CTP 股票期权行情网关 (Market Data Gateway)
    职责：仅负责连接柜台、登录、订阅、解析原生数据，并推入内存队列。
    支持股票 ETF 期权（SSE/SZSE），推送 5 档买卖盘。
    """

    def __init__(self, config: dict, tick_queue: queue.Queue):
        # 显式初始化两个父类
        BaseMdGateway.__init__(self, config, tick_queue)
        mdapi.CThostFtdcMdSpi.__init__(self)

        self.symbol_exchange_map = self.config.get("symbol_exchange_map", {})
        # 期权元数据映射：instrument_id -> {underlying_symbol, strike_price, contract_type, expiry_date}
        self.option_meta_map = self.config.get("option_meta_map", {})

    def connect(self):
        """外部调用：发起连接"""
        front_addr = self.config.get("front_address")
        if not front_addr:
            logging.error("CTP股票期权行情网关启动失败: 缺少 front_address 配置")
            return

        logging.info(f"CTP股票期权行情网关正在连接前置机: {front_addr}")

        os.makedirs("logs", exist_ok=True)
        self.api = mdapi.CThostFtdcMdApi.CreateFtdcMdApi("logs/ctp_sopt_md_")
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
            logging.info("CTP股票期权行情网关已安全释放")

    # ==========================================================
    # 以下为 CTP 原生回调函数 (C++ Override)
    # ==========================================================

    def OnFrontConnected(self) -> "void":
        """回调：前置机连接成功"""
        self.is_connected = True
        logging.info("CTP股票期权行情前置机连接成功！正在发起登录...")

        # 行情通道不验证密码，空登录即可
        req = mdapi.CThostFtdcReqUserLoginField()
        self.api.ReqUserLogin(req, 0)

    def OnFrontDisconnected(self, nReason: int) -> "void":
        """回调：前置机断开"""
        self.is_connected = False
        self.is_logged_in = False
        logging.warning(f"CTP股票期权行情前置机断开连接，原因代码: {nReason}")

    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast) -> "void":
        """回调：登录回执"""
        if pRspInfo is not None and pRspInfo.ErrorID != 0:
            logging.error(f"股票期权行情登录失败: {pRspInfo.ErrorMsg}")
            return

        self.is_logged_in = True
        trading_day = self.api.GetTradingDay()
        logging.info(f"CTP股票期权行情登录成功! 当前交易日: {trading_day}")

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
        logging.info(f"发送股票期权订阅请求，合约数量: {len(symbols)}")

    def OnRtnDepthMarketData(self, pDepthMarketData) -> "void":
        """
        回调：核心行情推送 (Tick 数据到达)
        构造 StockOptionLevel1TickData，包含 5 档买卖盘。
        """
        if not pDepthMarketData or not pDepthMarketData.InstrumentID:
            return

        # 1. 时间字段极速整型化
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

        # 2. 定义乘数
        M = 10000

        raw_instrument_id = pDepthMarketData.InstrumentID

        # 兼容处理：如果是 bytes 就解码为 str，并去除末尾空字节/空格
        if isinstance(raw_instrument_id, bytes):
            raw_instrument_id = raw_instrument_id.decode('gbk')
        instrument_id = raw_instrument_id.split('\x00')[0].strip()

        # 3. 安全取价（CTP 用 1e30 表示空值）
        def _safe_price(v):
            return 0 if v > 1e30 else int(v * M)

        # 4. 从 option_meta_map 填充期权专属字段
        meta = self.option_meta_map.get(instrument_id, {})

        # 5. 构造 StockOptionLevel1TickData
        tick_obj = StockOptionLevel1TickData(
            instrument_id=instrument_id,
            exchange_id=self.symbol_exchange_map.get(instrument_id, ""),

            trade_date=trade_date_val,
            action_date=action_date_val,
            update_time=update_time_val,
            update_millisec=int(pDepthMarketData.UpdateMillisec),
            local_time_ns=time.time_ns(),

            last_price=_safe_price(pDepthMarketData.LastPrice),
            volume=int(pDepthMarketData.Volume),
            turnover=0 if pDepthMarketData.Turnover > 1e30 else int(pDepthMarketData.Turnover * 100),
            open_interest=int(pDepthMarketData.OpenInterest),

            bid_price_1=_safe_price(pDepthMarketData.BidPrice1),
            bid_volume_1=int(pDepthMarketData.BidVolume1),
            ask_price_1=_safe_price(pDepthMarketData.AskPrice1),
            ask_volume_1=int(pDepthMarketData.AskVolume1),

            open_price=_safe_price(pDepthMarketData.OpenPrice),
            highest_price=_safe_price(pDepthMarketData.HighestPrice),
            lowest_price=_safe_price(pDepthMarketData.LowestPrice),
            average_price=_safe_price(pDepthMarketData.AveragePrice),
            upper_limit_price=_safe_price(pDepthMarketData.UpperLimitPrice),
            lower_limit_price=_safe_price(pDepthMarketData.LowerLimitPrice),

            # 期权专属
            underlying_symbol=meta.get('underlying_symbol', ''),
            strike_price=meta.get('strike_price', 0),
            contract_type=meta.get('contract_type', ''),
            expiry_date=meta.get('expiry_date', 0),

            # 5 档买卖盘（2-5 档）
            bid_price_2=_safe_price(pDepthMarketData.BidPrice2),
            bid_volume_2=int(pDepthMarketData.BidVolume2),
            bid_price_3=_safe_price(pDepthMarketData.BidPrice3),
            bid_volume_3=int(pDepthMarketData.BidVolume3),
            bid_price_4=_safe_price(pDepthMarketData.BidPrice4),
            bid_volume_4=int(pDepthMarketData.BidVolume4),
            bid_price_5=_safe_price(pDepthMarketData.BidPrice5),
            bid_volume_5=int(pDepthMarketData.BidVolume5),

            ask_price_2=_safe_price(pDepthMarketData.AskPrice2),
            ask_volume_2=int(pDepthMarketData.AskVolume2),
            ask_price_3=_safe_price(pDepthMarketData.AskPrice3),
            ask_volume_3=int(pDepthMarketData.AskVolume3),
            ask_price_4=_safe_price(pDepthMarketData.AskPrice4),
            ask_volume_4=int(pDepthMarketData.AskVolume4),
            ask_price_5=_safe_price(pDepthMarketData.AskPrice5),
            ask_volume_5=int(pDepthMarketData.AskVolume5),
        )

        # 推入内存队列，网关的职责到此结束
        self.tick_queue.put(tick_obj)
