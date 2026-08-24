"""
期货合约信息仓库（精简版）
- 从原 quantlab/repository/future/future_info_repo.py 迁移
- 移除了 upsert_batch / get_product_exchange_map
- 只保留 run_market_data.py 需要的 get_active_instruments
- 新增 get_active_instruments_detail 返回完整合约信息
"""
from sqlalchemy import text
from typing import List, Dict, Any


# 期货分类规则
STOCK_INDEX_PRODUCTS = {'IF', 'IH', 'IC', 'IM'}  # 股指期货
BOND_PRODUCTS = {'T', 'TF', 'TS', 'TL'}          # 国债期货


def classify_future(product_id: str) -> str:
    """根据 product_id 判断期货子类型"""
    pid = product_id.upper()
    if pid in STOCK_INDEX_PRODUCTS:
        return 'STOCK_INDEX'
    if pid in BOND_PRODUCTS:
        return 'BOND'
    return 'COMMODITY'


class FutureInfoRepo:
    TABLE = 'future_info'

    def __init__(self, engine):
        self.engine = engine

    def get_active_instruments(self, exchange_id: str = 'CFFEX') -> List[str]:
        """从数据库获取指定交易所的所有活跃期货合约 ID"""
        sql = f"""
        SELECT instrument_id 
        FROM {self.TABLE} 
        WHERE exchange_id = :exchange_id 
          AND status = 1 
          AND delist_date >= CURRENT_DATE
        """
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), {"exchange_id": exchange_id})
            return [row[0] for row in result]

    def get_active_instruments_detail(self, exchange_id: str = None) -> List[Dict[str, Any]]:
        """获取活跃期货合约的完整信息"""
        sql = f"""
        SELECT instrument_id, exchange_id, instrument_name, product_id,
               multiplier, tick_size, has_night_session,
               delivery_date, delivery_month, list_date, delist_date,
               margin_rate, fee_type, open_fee, close_fee, close_today_fee
        FROM {self.TABLE}
        WHERE status = 1 AND delist_date >= CURRENT_DATE
        """
        params = {}
        if exchange_id:
            sql += " AND exchange_id = :exchange_id"
            params["exchange_id"] = exchange_id
        sql += " ORDER BY exchange_id, product_id, instrument_id"

        with self.engine.connect() as conn:
            result = conn.execute(text(sql), params)
            rows = []
            for row in result:
                rows.append({
                    "symbol": row[0],
                    "exchange": row[1],
                    "name": row[2],
                    "product_id": row[3],
                    "multiplier": float(row[4]),
                    "tick_size": float(row[5]),
                    "has_night_session": bool(row[6]),
                    "delivery_date": str(row[7]) if row[7] else None,
                    "delivery_month": int(row[8]) if row[8] else None,
                    "list_date": str(row[9]) if row[9] else None,
                    "delist_date": str(row[10]) if row[10] else None,
                    "margin_rate": float(row[11]) if row[11] else None,
                    "fee_type": row[12],
                    "open_fee": float(row[13]) if row[13] else None,
                    "close_fee": float(row[14]) if row[14] else None,
                    "close_today_fee": float(row[15]) if row[15] else None,
                    "future_type": classify_future(row[3]),
                })
            return rows
