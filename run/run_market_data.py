"""
qt2-server 行情接收引擎主入口（Job 模式）

功能：
1. 每日自动接收 CTP 期货行情（可扩展期权/股票）
2. 通过 ZeroMQ 进行行情分发，下游可订阅
3. 二进制极速落盘（bin 格式，对齐 ClickHouse）
4. Redis 监控上报（系统健康 + 最新行情快照）

架构：
- 网关层：BaseMdGateway -> CtpMdGateway / StockL2Gateway
- 录制层：BaseRecorder -> FutureTickRecorder / OptionTickRecorder / StockL2Recorder
- 配置驱动：.env 默认配置 + 命令行参数覆盖

用法：
  # 默认按 .env 配置启动
  python run/run_market_data.py

  # 命令行覆盖：只跑 CTP 期货
  python run/run_market_data.py --gateway ctp --assets future

  # CTP 期货+期权
  python run/run_market_data.py --gateway ctp --assets future,option

  # 只跑 CTP 期权
  python run/run_market_data.py --gateway ctp --assets option
"""
import sys
import os
import time
import queue
import argparse
import threading
from datetime import datetime, timedelta

# 确保项目根目录在 sys.path 中，支持 `python run/run_market_data.py` 直接运行
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from core.util.db_util import get_db_engine
from core.util.log_util import Logger
from core.util.process_util import ProcessUtil
from core.setting.setting import (
    GATEWAYS, ZMQ_BIND_URL, DATA_DIR,
    CTP_MD_FRONT_ADDRESS, CTP_SUBSCRIBE_EXCHANGES, CTP_SUBSCRIBE_ASSET_TYPES,
)
from repository.trade_calendar_repo import TradeCalendarRepo
from repository.instrument.future_info_repo import FutureInfoRepo
from repository.instrument.option_info_repo import OptionInfoRepo

# 网关注册表（配置驱动，按 gateways 列表启动）
from gateway.ctp.ctp_md_gateway import CtpMdGateway
# from gateway.stock_l2.stock_l2_gateway import StockL2Gateway    # 未来

# 录制器
from data_process.future_tick_recorder import FutureTickRecorder
from data_process.option_tick_recorder import OptionTickRecorder
# from data_process.stock_l2_recorder import StockL2Recorder      # 未来

# 网关注册表
GATEWAY_REGISTRY = {
    "ctp": CtpMdGateway,
    # "stock_l2": StockL2Gateway,    # 未来
}

# 录制器注册表：asset_type -> (RecorderClass, 落盘子路径)
RECORDER_REGISTRY = {
    "FUTURE": (FutureTickRecorder, "future/level1/tick"),
    "OPTION": (OptionTickRecorder, "option/level1/tick"),
    # "STOCK": (StockL2Recorder, "stock/level2/tick"),   # 未来
}


def parse_args():
    """解析命令行参数，未传则走 .env 默认配置"""
    parser = argparse.ArgumentParser(
        description="qt2-server 行情接收引擎（Job 模式）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--gateway", type=str, default=None,
        help="启用的网关，逗号分隔（覆盖 .env 的 GATEWAYS，如 ctp / ctp,stock_l2）",
    )
    parser.add_argument(
        "--assets", type=str, default=None,
        help="订阅的资产类型，逗号分隔（覆盖 .env 的 CTP_SUBSCRIBE_ASSET_TYPES，如 future / future,option）",
    )
    return parser.parse_args()


def _parse_csv(value: str, default: list, upper: bool = True) -> list:
    """将逗号分隔字符串解析为列表，None 返回 default"""
    if value is None:
        return default
    items = [item.strip() for item in value.split(",") if item.strip()]
    return [item.upper() for item in items] if upper else items


def should_auto_exit() -> bool:
    """
    检查当前是否处于强制退出时间段
    1. 白盘：15:40 - 15:45 (提前退出，给 15:30 的盘后清洗作业留出充足空档和释放文件锁)
    2. 夜盘：02:40 - 03:00 (夜盘 02:30 彻底结束，留出缓冲时间)
    """
    now = datetime.now()
    hm = now.strftime("%H:%M")

    if "15:40" <= hm <= "15:45":
        return True
    if "02:45" <= hm <= "03:00":
        return True

    return False


def check_trading_time():
    """节假日（考虑周五夜盘）拦截"""
    engine = get_db_engine()
    calendar_repo = TradeCalendarRepo(engine)

    now = datetime.now()

    # 凌晨跨日偏移计算
    check_time = now
    if now.hour < 4:
        check_time = now - timedelta(days=1)
        Logger.info(f"🌙 凌晨时段触发，逻辑检查日期向后偏移至: {check_time.strftime('%Y-%m-%d')}")

    today_date = check_time.date()
    today_str = today_date.strftime('%Y-%m-%d')
    is_friday = check_time.weekday() == 4

    start_check_date = today_str
    end_check_date = (check_time + timedelta(days=15)).strftime('%Y-%m-%d')
    valid_days = calendar_repo.get_trading_days(start_date=start_check_date, end_date=end_check_date)

    # 规则 1：如果"逻辑今日"不是交易日，直接退出
    if today_str not in valid_days:
        Logger.info(f"🛌 休市拦截：逻辑检查日 {today_str} 为非交易日，行情引擎退出。")
        sys.exit(0)

    # 规则 2：如果是夜盘起步时段 (晚上 18:00 以后拉起)
    if now.hour >= 18:
        try:
            today_idx = valid_days.index(today_str)
            next_trading_str = valid_days[today_idx + 1]
            next_trading_date = datetime.strptime(next_trading_str, '%Y-%m-%d').date()

            diff_days = (next_trading_date - today_date).days

            if (is_friday and diff_days > 3) or (not is_friday and diff_days > 1):
                Logger.info(f"🛌 休市拦截：下个交易日为 {next_trading_str} (间隔 {diff_days} 天)，遇到法定节假日，今晚无连续交易！")
                sys.exit(0)

        except IndexError:
            Logger.warning("⚠️ 交易日历数据可能未更新，安全起见默认放行。")

    Logger.info("✅ 交易时段核对通过，准许启动行情引擎。")


def get_ctp_instruments(asset_types: list) -> tuple:
    """
    从数据库拉取 CTP 需要订阅的合约清单
    根据 asset_types 参数决定拉取期货/期权/两者
    返回: (symbol_exchange_map, symbol_asset_type_map, subscribe_list)
    """
    engine = get_db_engine()
    exchanges = CTP_SUBSCRIBE_EXCHANGES

    symbol_exchange_map = {}
    symbol_asset_type_map = {}

    # --- 期货合约 ---
    if 'FUTURE' in asset_types:
        future_repo = FutureInfoRepo(engine)
        for ex in exchanges:
            instruments = future_repo.get_active_instruments(ex)
            if instruments:
                for symbol in instruments:
                    symbol_exchange_map[symbol] = ex
                    symbol_asset_type_map[symbol] = 'FUTURE'
                Logger.info(f"📌 [期货] {ex} 交易所加载了 {len(instruments)} 个活跃合约。")

    # --- 期权合约 ---
    if 'OPTION' in asset_types:
        option_repo = OptionInfoRepo(engine)
        for ex in exchanges:
            instruments = option_repo.get_active_instruments(ex)
            if instruments:
                for symbol in instruments:
                    symbol_exchange_map[symbol] = ex
                    symbol_asset_type_map[symbol] = 'OPTION'
                Logger.info(f"📌 [期权] {ex} 交易所加载了 {len(instruments)} 个活跃合约。")

    Logger.info(f"✅ CTP 全市场共加载 {len(symbol_exchange_map)} 个待订阅合约。")
    return symbol_exchange_map, symbol_asset_type_map, list(symbol_exchange_map.keys())


def build_ctp_config(asset_types: list) -> dict:
    """构建 CTP 网关配置"""
    symbol_exchange_map, symbol_asset_type_map, subscribe_list = get_ctp_instruments(asset_types)

    # CTP 合约代码大小写规则
    exchange_case_rules = {
        'SHFE': str.lower,
        'DCE':  str.lower,
        'INE':  str.lower,
        'GFEX': str.lower,
        'CFFEX': str.upper,
        'CZCE': str.upper
    }

    # 清洗并生成标准化的 CTP 订阅字典和列表
    cleaned_symbol_exchange_map = {}
    cleaned_symbol_asset_type_map = {}
    cleaned_subscribe_list = []

    for symbol in subscribe_list:
        exchange = symbol_exchange_map[symbol]
        asset_type = symbol_asset_type_map[symbol]
        format_func = exchange_case_rules.get(exchange.upper(), lambda x: x)
        ctp_symbol = format_func(symbol)

        cleaned_symbol_exchange_map[ctp_symbol] = exchange
        cleaned_symbol_asset_type_map[ctp_symbol] = asset_type
        cleaned_subscribe_list.append(ctp_symbol)

    Logger.info(f"✅ 合约清洗完成，共生成 {len(cleaned_subscribe_list)} 个 CTP 标准订阅代码")

    # 加载期权元数据映射（用于网关填充 OptionLevel1TickData 专属字段）
    option_meta_map = {}
    if 'OPTION' in asset_types:
        engine = get_db_engine()
        option_repo = OptionInfoRepo(engine)
        raw_meta_map = option_repo.get_option_meta_map()  # 全交易所
        # 清洗 key 为 CTP 标准格式
        for symbol, meta in raw_meta_map.items():
            exchange = symbol_exchange_map.get(symbol, '')
            format_func = exchange_case_rules.get(exchange.upper(), lambda x: x)
            ctp_symbol = format_func(symbol)
            option_meta_map[ctp_symbol] = meta
        Logger.info(f"✅ 期权元数据加载完成，共 {len(option_meta_map)} 个合约")

    return {
        "front_address": CTP_MD_FRONT_ADDRESS,
        "subscribe_list": cleaned_subscribe_list,
        "symbol_exchange_map": cleaned_symbol_exchange_map,
        "symbol_asset_type_map": cleaned_symbol_asset_type_map,
        "option_meta_map": option_meta_map,
    }


def main():
    args = parse_args()

    # 命令行参数覆盖 .env 配置
    enabled_gateways = _parse_csv(args.gateway, GATEWAYS, upper=False)
    asset_types = _parse_csv(args.assets, CTP_SUBSCRIBE_ASSET_TYPES)

    # 单例锁名按服务组合区分，支持多实例并行（如 ctp+future 和 ctp+option 不互斥）
    lock_name = f"run_market_data_{'_'.join(enabled_gateways)}_{'_'.join(asset_types)}"

    # 尝试获取单例锁
    if not ProcessUtil.acquire_singleton_lock(lock_name):
        Logger.error(f"🚫 拦截：已有相同服务实例运行（lock={lock_name}），为防数据污染，本次启动主动退出。")
        sys.exit(0)

    check_trading_time()

    Logger.info("========================================")
    Logger.info(" 🚀 启动 qt2-server 行情接收引擎...")
    Logger.info("========================================")

    # 1. 读取全局配置
    zmq_bind_url = ZMQ_BIND_URL
    data_dir_base = DATA_DIR

    Logger.info(f"📋 启用的网关: {enabled_gateways}")
    Logger.info(f"� 订阅资产类型: {asset_types}")
    Logger.info(f"�📡 ZMQ 广播地址: {zmq_bind_url}")
    Logger.info(f"🔒 单例锁: {lock_name}")

    # 2. 创建线程安全的内存队列（所有网关共享）
    tick_queue = queue.Queue()

    # 2.1 创建共享的 ZMQ Publisher（避免多 Recorder 重复 bind 同一端口）
    from core.util.zmq_util import ZmqPublisher
    shared_zmq_publisher = ZmqPublisher(bind_url=zmq_bind_url)

    # 3. 按资产类型动态启动录制器
    recorders = []
    for asset_type in asset_types:
        recorder_entry = RECORDER_REGISTRY.get(asset_type)
        if not recorder_entry:
            Logger.warning(f"⚠️ 未知资产类型: {asset_type}，跳过。")
            continue

        recorder_class, sub_path = recorder_entry
        recorder = recorder_class(
            tick_queue,
            data_dir=os.path.join(data_dir_base, sub_path),
            zmq_bind_url=zmq_bind_url,
            zmq_publisher=shared_zmq_publisher
        )
        recorders.append(recorder)
        Logger.info(f"  ✅ 启动录制器: {asset_type} -> {sub_path}")

    if not recorders:
        Logger.error("🚫 没有可用的录制器，请检查 --assets 参数。")
        sys.exit(1)

    # 4. 启动网关
    gateways = []
    for gw_name in enabled_gateways:
        gw_class = GATEWAY_REGISTRY.get(gw_name)
        if not gw_class:
            Logger.warning(f"⚠️ 未知网关类型: {gw_name}，跳过。")
            continue

        if gw_name == "ctp":
            config = build_ctp_config(asset_types)
        else:
            Logger.warning(f"⚠️ 网关 {gw_name} 的配置构建尚未实现，跳过。")
            continue

        gw = gw_class(config, tick_queue)
        gw.connect()
        gateways.append(gw)

    # 5. 主线程监控
    try:
        while True:
            if should_auto_exit():
                Logger.info("🛑 当前已进入强制退出时间段，程序即将退出。")
                break

            time.sleep(5.0)
            current_qsize = tick_queue.qsize()

            Logger.info(f"📊 监控 | 内存队列积压: {current_qsize} | 活跃网关: {len(gateways)} | 录制器: {len(recorders)}")

    except KeyboardInterrupt:
        Logger.info("🛑 收到退出指令 (Ctrl+C)，正在安全关闭系统...")
    finally:
        Logger.info("正在释放网关连接并停止录制器...")
        for gw in gateways:
            gw.release()
        for recorder in recorders:
            recorder.stop()
        Logger.info("✅ 系统已安全退出。")


if __name__ == '__main__':
    main()
