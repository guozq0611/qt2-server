"""
期货合约信息仓库（精简版）
- 从原 quantlab/repository/future/future_info_repo.py 迁移
- 移除了 upsert_batch / get_product_exchange_map
- 只保留 run_market_data.py 需要的 get_active_instruments
"""
from sqlalchemy import text
from typing import List


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
