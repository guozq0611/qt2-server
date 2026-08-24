"""
基础数据同步入口脚本

用法:
    # 同步全部基础数据（期货合约信息 + 交易日历）
    python run/run_sync_data.py

    # 仅同步期货合约信息
    python run/run_sync_data.py --future-info

    # 仅同步交易日历
    python run/run_sync_data.py --trade-calendar --start 20250101 --end 20261231

    # 同步全部合约（含已退市）
    python run/run_sync_data.py --future-info --contract-type 3
"""
import argparse
import sys
import os

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.service.data_sync_service import DataSyncService
from core.util.log_util import Logger


def main():
    parser = argparse.ArgumentParser(description="qt2-server 基础数据同步")
    parser.add_argument('--future-info', action='store_true', help='同步期货合约信息')
    parser.add_argument('--trade-calendar', action='store_true', help='同步交易日历')
    parser.add_argument('--contract-type', type=str, default='1',
                        help='合约类型: 1=活跃(默认), 2=非活跃, 3=已退市')
    parser.add_argument('--start', type=str, default=None, help='交易日历开始日期 YYYYMMDD')
    parser.add_argument('--end', type=str, default=None, help='交易日历结束日期 YYYYMMDD')
    args = parser.parse_args()

    # 如果没有指定任何 flag，则同步全部
    sync_all = not (args.future_info or args.trade_calendar)

    service = DataSyncService()

    try:
        if sync_all or args.future_info:
            Logger.info("=" * 50)
            Logger.info("同步期货合约信息 (future_info)")
            Logger.info("=" * 50)
            service.sync_future_info(contract_type=args.contract_type)

        if sync_all or args.trade_calendar:
            Logger.info("=" * 50)
            Logger.info("同步交易日历 (trade_calendar)")
            Logger.info("=" * 50)
            service.sync_trade_calendar(start_date=args.start, end_date=args.end)

        Logger.info("数据同步全部完成")

    except Exception as e:
        Logger.error(f"数据同步失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
