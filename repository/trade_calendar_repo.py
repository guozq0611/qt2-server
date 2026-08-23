"""
交易日历仓库（精简版）
- 从原 quantlab/repository/trade_calendar_repo.py 迁移
- 移除了 upsert_batch / get_trade_calendar_maps（回测专用）
- 只保留 run_market_data.py 需要的 get_trading_days / load_trade_calendar
"""
from sqlalchemy import text
import pandas as pd
from datetime import date, timedelta
from typing import Dict


class TradeCalendarRepo:

    TABLE = 'trade_calendar'

    def __init__(self, engine):
        self.engine = engine

    def get_last_trade_date(self):
        sql = """
        SELECT MAX(trade_date) as trade_date FROM trade_calendar
        """
        with self.engine.connect() as conn:
            result = conn.execute(text(sql)).scalar()
            return result

    def load_trade_calendar(self, start_date: str = None, end_date: str = None):
        where_conditions = ["exchange = 'SSE'"]
        if start_date is not None and start_date != '':
            where_conditions.append(f"trade_date >= '{start_date}'")
        if end_date is not None and end_date != '':
            where_conditions.append(f"trade_date <= '{end_date}'")

        where_clause = " AND ".join(where_conditions)

        sql = f"""
        SELECT
            trade_date,
            exchange,
            is_open,
            prev_trade_date
        FROM trade_calendar
        """

        if where_clause:
            sql += f" WHERE {where_clause}"

        sql += " ORDER BY trade_date"

        with self.engine.connect() as conn:
            df = pd.read_sql(sql, conn)

        return df

    def get_trading_days(self, start_date: str = None, end_date: str = None) -> list:
        """
        获取指定时间段内的有效交易日列表
        返回格式: ['2024-11-14', '2024-11-15', ...]
        """
        df = self.load_trade_calendar(start_date, end_date)

        if df.empty:
            return []

        open_days_df = df[df['is_open'] == 1]
        trading_days = pd.to_datetime(open_days_df['trade_date']).dt.strftime('%Y-%m-%d').tolist()

        return trading_days
