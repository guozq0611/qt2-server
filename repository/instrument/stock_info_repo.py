"""
股票合约信息仓库（占位）
- 未来接入股票 L2 行情时实现
- 查询股票代码清单（沪深两市）
"""
from sqlalchemy import text
from typing import List


class StockInfoRepo:
    """
    股票合约信息仓库（占位）

    未来实现要点：
    - 表结构：stock_info（symbol, exchange, name, status, delist_date）
    - get_active_stocks: 查活跃股票代码
    """

    TABLE = 'stock_info'

    def __init__(self, engine):
        self.engine = engine

    def get_active_stocks(self, exchange: str = 'SSE') -> List[str]:
        """从数据库获取指定交易所的所有活跃股票代码（占位）"""
        sql = f"""
        SELECT symbol 
        FROM {self.TABLE} 
        WHERE exchange = :exchange 
          AND status = 1 
          AND delist_date >= CURRENT_DATE
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql), {"exchange": exchange})
                return [row[0] for row in result]
        except Exception:
            return []
