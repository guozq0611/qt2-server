"""
基础数据同步服务
- future_info: 期货合约信息（从 Tushare fut_basic 同步）
- trade_calendar: 交易日历（从 Tushare trade_cal 同步）

迁移自 quantlab 的 PreFutureMarketJob 和 TradeCalendarRepo.upsert_batch
"""
import re
import pandas as pd
from datetime import datetime
from sqlalchemy import text

from core.util.log_util import Logger
from core.util.db_util import get_db_engine
from core.wrapper.tushare_wrapper import TushareWrapper


class DataSyncService:
    """
    基础数据同步服务
    从 Tushare 拉取数据，清洗后写入 MySQL
    """

    EXCHANGES = ['CFFEX', 'SHFE', 'DCE', 'CZCE', 'INE', 'GFEX']

    def __init__(self):
        self.engine = get_db_engine()
        self.ts_wrapper = TushareWrapper.get_instance()

    # ==========================================================
    # future_info 同步
    # ==========================================================

    def sync_future_info(self, contract_type: str = '1') -> int:
        """
        同步期货合约信息到 future_info 表
        :param contract_type: '1'=活跃合约, '2'=非活跃, '3'=已退市, None=全部
        :return: 写入记录数
        """
        Logger.info("开始同步期货合约信息...")

        # 1. 拉取原始数据
        raw_df = self.ts_wrapper.get_future_info(
            exchanges=self.EXCHANGES,
            contract_type=contract_type,
        )
        if raw_df is None or raw_df.empty:
            Logger.warning("Tushare 未返回期货合约数据")
            return 0

        Logger.info(f"从 Tushare 拉取到 {len(raw_df)} 条合约记录")

        # 2. 数据清洗
        clean_df = self._transform_future_info(raw_df)
        if clean_df.empty:
            Logger.warning("清洗后无有效数据")
            return 0

        # 3. 写入数据库
        count = self._upsert_future_info(clean_df)
        Logger.info(f"future_info 同步完成，共 {count} 条记录")

        # 4. 清理过期合约
        self._clean_expired_contracts()

        return count

    def _transform_future_info(self, df: pd.DataFrame) -> pd.DataFrame:
        """数据清洗：提取乘数、tick_size，设置保证金/手续费/夜盘等规则"""
        if df is None or df.empty:
            return pd.DataFrame()

        df = df.copy()

        # 0. 基础衍生字段
        df['currency'] = 'CNY'
        df['settle_type'] = df['exchange_id'].apply(
            lambda x: 'CASH' if x == 'CFFEX' else 'PHYSICAL'
        )

        # 1. 清洗乘数与最小变动价位（兼容 Tushare 不同列名）
        def get_final_multiplier(row):
            raw_m = self._clean_numeric(row.get('multiplier'))
            raw_p = self._clean_numeric(row.get('per_unit'))
            return raw_m if raw_m else (raw_p if raw_p else 1.0)

        def get_tick_size(row):
            tick = self._clean_numeric(row.get('quote_unit_desc'))
            if not tick:
                tick = self._clean_numeric(row.get('min_perice_chg'))
            return tick if tick else 1.0

        df['final_multiplier'] = df.apply(get_final_multiplier, axis=1)
        df['final_min_tick'] = df.apply(get_tick_size, axis=1)

        # 2. 字段重命名
        df = df.rename(columns={
            'last_ddate': 'delivery_date',
            'name': 'instrument_name',
            'fut_code': 'product_id',
            'd_month': 'delivery_month',
        })

        # 3. 交割月份格式化（4位→6位：1811→201811）
        if 'delivery_month' in df.columns:
            df['delivery_month'] = df['delivery_month'].apply(self._format_delivery_month)

        # 4. 日期转换
        for col in ['list_date', 'delist_date', 'delivery_date']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format='%Y%m%d', errors='coerce')
                df[col] = df[col].apply(lambda x: x.date() if pd.notnull(x) else None)

        # 5. 按品种设置保证金/手续费/夜盘
        df[['margin_rate', 'fee_type', 'open_fee', 'close_fee',
            'close_today_fee', 'has_night_session', 'max_limit_order_vol']] = df.apply(
            self._apply_instrument_rules, axis=1
        )

        # 6. 状态推导
        today = pd.Timestamp.today().date()
        df['status'] = df['delist_date'].apply(
            lambda x: 0 if pd.notnull(x) and x < today else 1
        )

        keep_cols = [
            'instrument_id', 'exchange_id', 'instrument_name', 'product_id',
            'currency', 'settle_type',
            'delivery_month', 'final_multiplier', 'final_min_tick',
            'status', 'has_night_session', 'max_limit_order_vol',
            'margin_rate', 'fee_type', 'open_fee', 'close_fee', 'close_today_fee',
            'list_date', 'delist_date', 'delivery_date',
        ]

        available_cols = [c for c in keep_cols if c in df.columns]
        df = df[available_cols].rename(columns={
            'final_multiplier': 'multiplier',
            'final_min_tick': 'tick_size',
        })

        return df

    @staticmethod
    def _clean_numeric(value):
        """从字符串中提取数值"""
        if pd.isna(value):
            return None
        match = re.search(r"([0-9]+\.?[0-9]*)", str(value))
        return float(match.group(1)) if match else None

    @staticmethod
    def _format_delivery_month(m):
        """交割月份格式化：4位→6位（1811→201811），6位原样返回"""
        if pd.isna(m) or not str(m).strip():
            return None
        m_str = str(m).strip()
        if len(m_str) == 4:
            return int(f"20{m_str}")
        elif len(m_str) == 6:
            return int(m_str)
        return None

    @staticmethod
    def _apply_instrument_rules(row):
        """按品种设置保证金率、手续费、夜盘等"""
        prod = str(row.get('product_id', '')).upper()
        exchange = str(row.get('exchange_id', '')).upper()

        margin_rate = 0.12
        fee_type = 'RATIO'
        open_fee = 0.0001
        close_fee = 0.0001
        close_today_fee = 0.0001
        max_limit_vol = 500
        has_night = 0 if exchange == 'CFFEX' else 1

        if prod in ('IF', 'IH'):
            margin_rate, open_fee, close_fee, close_today_fee = 0.12, 0.000023, 0.000023, 0.000345
        elif prod in ('IC', 'IM'):
            margin_rate, open_fee, close_fee, close_today_fee = 0.14, 0.000023, 0.000023, 0.00023
        elif prod in ('T', 'TF', 'TS', 'TL'):
            margin_rate, fee_type, open_fee, close_fee, close_today_fee = 0.03, 'FIXED', 3.0, 3.0, 0.0
        elif prod == 'SA':
            margin_rate, fee_type, open_fee, close_fee, close_today_fee = 0.12, 'FIXED', 3.5, 3.5, 3.5

        return pd.Series([margin_rate, fee_type, open_fee, close_fee,
                          close_today_fee, has_night, max_limit_vol])

    def _upsert_future_info(self, df: pd.DataFrame, batch_size: int = 1000) -> int:
        """批量写入 future_info 表（ON DUPLICATE KEY UPDATE）"""
        if df.empty:
            return 0

        columns = df.columns.tolist()
        update_fields = ', '.join([
            f"{col} = VALUES({col})" for col in columns
            if col not in ('instrument_id', 'exchange_id')
        ])

        sql = f"""
        INSERT INTO future_info ({', '.join(columns)})
        VALUES ({', '.join([f':{col}' for col in columns])})
        ON DUPLICATE KEY UPDATE {update_fields}
        """

        records = df.to_dict('records')
        total_rows = 0

        with self.engine.begin() as conn:
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                result = conn.execute(text(sql), batch)
                total_rows += result.rowcount

        return total_rows

    def _clean_expired_contracts(self):
        """将已过期的合约标记为失效"""
        sql = """
            UPDATE future_info
            SET status = 0
            WHERE delist_date < CURDATE() AND status = 1
        """
        try:
            with self.engine.begin() as conn:
                result = conn.execute(text(sql))
                if result.rowcount > 0:
                    Logger.info(f"已将 {result.rowcount} 个过期合约标记为失效")
        except Exception as e:
            Logger.error(f"清理过期合约失败: {e}")

    # ==========================================================
    # trade_calendar 同步
    # ==========================================================

    def sync_trade_calendar(self, start_date: str = None, end_date: str = None) -> int:
        """
        同步交易日历到 trade_calendar 表
        :param start_date: 开始日期 YYYYMMDD，默认当年1月1日
        :param end_date: 结束日期 YYYYMMDD，默认次年12月31日
        :return: 写入记录数
        """
        if start_date is None:
            start_date = f"{datetime.now().year}0101"
        if end_date is None:
            end_date = f"{datetime.now().year + 1}1231"

        Logger.info(f"开始同步交易日历: {start_date} ~ {end_date}")

        df = self.ts_wrapper.get_trade_calendar(start_date=start_date, end_date=end_date)
        if df is None or df.empty:
            Logger.warning("Tushare 未返回交易日历数据")
            return 0

        Logger.info(f"从 Tushare 拉取到 {len(df)} 条日历记录")

        count = self._upsert_trade_calendar(df)
        Logger.info(f"trade_calendar 同步完成，共 {count} 条记录")

        return count

    def _upsert_trade_calendar(self, df: pd.DataFrame, batch_size: int = 1000) -> int:
        """批量写入 trade_calendar 表"""
        if df.empty:
            return 0

        columns = ['trade_date', 'exchange', 'is_open', 'prev_trade_date']
        df = df[columns].copy()

        update_fields = ', '.join([f"{col} = VALUES({col})" for col in columns])

        sql = f"""
        INSERT INTO trade_calendar ({', '.join(columns)})
        VALUES ({', '.join([f':{col}' for col in columns])})
        ON DUPLICATE KEY UPDATE {update_fields}
        """

        records = df.to_dict('records')
        total_rows = 0

        with self.engine.begin() as conn:
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                result = conn.execute(text(sql), batch)
                total_rows += result.rowcount

        return total_rows
