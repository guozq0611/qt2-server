"""
Tushare API 封装（精简版）
- 仅保留 qt2-server 需要的 future_info 和 trade_calendar 数据获取
- 迁移自 quantlab/core/wrapper/tushare_wrapper.py
"""
import time
import pandas as pd
from typing import List

import tushare as ts
from core.setting.setting import TUSHARE_TOKEN
from core.util.log_util import Logger


# 交易所代码映射：qt2-server 内部标识 ↔ Tushare 后缀
_EXCHANGE_ID_TO_TS_POSTFIX = {
    'CFFEX': 'CFX',
    'DCE': 'DCE',
    'CZCE': 'ZCE',
    'SHFE': 'SHF',
    'INE': 'INE',
    'GFEX': 'GFE',
}

_TS_POSTFIX_TO_EXCHANGE_ID = {
    v: k for k, v in _EXCHANGE_ID_TO_TS_POSTFIX.items()
}


class TushareWrapper:
    """
    Tushare API 访问封装
    职责：网络请求、参数转换、分页限流、CTP 标识符标准化
    """

    _instance = None

    def __init__(self):
        if not TUSHARE_TOKEN:
            raise ValueError("TUSHARE_TOKEN 未配置，请在 .env 中设置")
        self.ts_pro = ts.pro_api(TUSHARE_TOKEN)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _fetch_with_pagination(self, api_func, limit: int = 2000, **kwargs) -> pd.DataFrame:
        """通用自动分页引擎"""
        all_data = []
        offset = 0

        while True:
            try:
                df = api_func(**kwargs, limit=limit, offset=offset)
                if df is None or df.empty:
                    break
                all_data.append(df)
                if len(df) < limit:
                    break
                offset += limit
                time.sleep(0.2)
            except Exception as e:
                Logger.error(f"Tushare 分页拉取失败 (offset={offset}): {e}")
                break

        if all_data:
            return pd.concat(all_data, ignore_index=True)
        return pd.DataFrame()

    @staticmethod
    def _standardize_ctp_symbol(df: pd.DataFrame, code_col: str = 'ts_code') -> pd.DataFrame:
        """将 Tushare 代码格式转换为 CTP 标准格式，产出 instrument_id 和 exchange_id"""
        if df is None or df.empty or code_col not in df.columns:
            return df

        df = df.copy()
        parts = df[code_col].str.split('.', expand=True)
        raw_instrument = parts[0]
        ts_postfix = parts[1].str.upper() if parts.shape[1] > 1 else pd.Series('UNKNOWN', index=df.index)

        df['exchange_id'] = ts_postfix.map(_TS_POSTFIX_TO_EXCHANGE_ID).fillna('UNKNOWN')

        # CTP 风格大小写规则
        exchange_case_rules = {
            'SHFE': str.lower, 'DCE': str.lower, 'INE': str.lower, 'GFEX': str.lower,
            'CFFEX': str.upper, 'CZCE': str.upper, 'ZCE': str.upper,
        }

        def _cvt_id(row):
            func = exchange_case_rules.get(row['exchange_id'], lambda x: x)
            return func(row['raw_inst'])

        df['raw_inst'] = raw_instrument
        df['instrument_id'] = df.apply(_cvt_id, axis=1)
        df.drop(columns=['raw_inst'], inplace=True)

        return df

    def get_trade_calendar(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取交易日历数据"""
        res = self.ts_pro.trade_cal(exchange='', start_date=start_date, end_date=end_date)
        if res is None or res.empty:
            return pd.DataFrame()

        # 计算 prev_trade_date（仅对 is_open=1 的行）
        res = res.sort_values(['cal_date']).reset_index(drop=True)
        open_dates = res[res['is_open'] == 1]['cal_date'].tolist()
        prev_map = {}
        for i in range(1, len(open_dates)):
            prev_map[open_dates[i]] = open_dates[i - 1]

        res['prev_trade_date'] = res['cal_date'].map(prev_map)
        res = res.rename(columns={'cal_date': 'trade_date'})
        res['trade_date'] = pd.to_datetime(res['trade_date'], format='%Y%m%d').dt.strftime('%Y-%m-%d')
        if 'prev_trade_date' in res.columns:
            res['prev_trade_date'] = pd.to_datetime(
                res['prev_trade_date'], format='%Y%m%d', errors='coerce'
            ).dt.strftime('%Y-%m-%d')

        return res[['trade_date', 'exchange', 'is_open', 'prev_trade_date']]

    def get_future_info(self, exchanges: List[str] = None, contract_type: str = '1') -> pd.DataFrame:
        """
        获取期货基础信息
        :param exchanges: 交易所列表，默认全部
        :param contract_type: '1'=活跃合约, '2'=非活跃, '3'=已退市, None=全部
        """
        if exchanges is None or len(exchanges) == 0:
            exchanges = list(_EXCHANGE_ID_TO_TS_POSTFIX.keys())

        fetch_result = []
        for exchange_id in exchanges:
            try:
                res = self.ts_pro.fut_basic(
                    exchange=exchange_id,
                    fut_type=contract_type,
                )
                if res is not None and not res.empty:
                    fetch_result.append(res)
            except Exception as e:
                Logger.error(f"获取 {exchange_id} 期货基础信息失败: {e}")

        if not fetch_result:
            return pd.DataFrame()

        df = pd.concat(fetch_result, ignore_index=True)

        # 标准化 CTP 代码
        df = self._standardize_ctp_symbol(df, code_col='ts_code')

        # 字段名标准化
        df = df.rename(columns={
            'name': 'instrument_name',
            'fut_code': 'product_id',
            'd_month': 'delivery_month',
        })

        # 剔除 Tushare 原始冗余字段
        cols_to_drop = ['ts_code', 'symbol', 'exchange']
        df = df.drop(columns=cols_to_drop, errors='ignore')

        return df
