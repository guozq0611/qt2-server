"""
期权合约信息仓库（占位）
- 未来接入期权行情时实现
- 查询期权合约清单，返回合约代码 + 标的 + 行权价 + 类型 + 到期日
"""
from sqlalchemy import text
from typing import List, Dict


class OptionInfoRepo:
    """
    期权合约信息仓库（占位）

    未来实现要点：
    - 表结构：option_info（instrument_id, exchange_id, underlying_symbol,
      strike_price, contract_type, expiry_date, status, delist_date）
    - get_active_instruments: 查活跃期权合约
    - get_option_meta: 查期权元数据（标的、行权价、类型、到期日），用于填充 OptionLevel1TickData
    """

    TABLE = 'option_info'

    def __init__(self, engine):
        self.engine = engine

    def get_active_instruments(self, exchange_id: str = 'CFFEX') -> List[str]:
        """从数据库获取指定交易所的所有活跃期权合约 ID（占位）"""
        sql = f"""
        SELECT instrument_id 
        FROM {self.TABLE} 
        WHERE exchange_id = :exchange_id 
          AND status = 1 
          AND delist_date >= CURDATE()
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql), {"exchange_id": exchange_id})
                return [row[0] for row in result]
        except Exception:
            # 表可能尚未创建
            return []

    def get_option_meta_map(self, exchange_id: str = 'CFFEX') -> Dict[str, dict]:
        """
        获取期权元数据映射（占位）
        返回: {instrument_id: {underlying_symbol, strike_price, contract_type, expiry_date}}
        """
        sql = f"""
        SELECT instrument_id, underlying_symbol, strike_price, contract_type, expiry_date
        FROM {self.TABLE}
        WHERE exchange_id = :exchange_id
          AND status = 1
          AND delist_date >= CURDATE()
        """
        mapping = {}
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql), {"exchange_id": exchange_id})
                for row in result:
                    mapping[row[0]] = {
                        'underlying_symbol': row[1],
                        'strike_price': int(row[2] * 10000) if row[2] else 0,
                        'contract_type': row[3],
                        'expiry_date': int(str(row[4]).replace('-', '')) if row[4] else 0,
                    }
        except Exception:
            pass
        return mapping
