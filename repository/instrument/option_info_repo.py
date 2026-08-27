"""
期权合约信息仓库
- 查询期权合约清单
- 查询期权元数据（标的、行权价、类型、到期日），用于填充 OptionLevel1TickData
"""
from sqlalchemy import text
from typing import List, Dict


class OptionInfoRepo:
    """
    期权合约信息仓库

    表结构：option_info（instrument_id, exchange_id, underlying_symbol,
      strike_price, contract_type, expiry_date, multiplier, tick_size, status, delist_date）
    """

    TABLE = 'option_info'

    def __init__(self, engine):
        self.engine = engine

    def get_active_instruments(self, exchange_id: str = 'CFFEX') -> List[str]:
        """从数据库获取指定交易所的所有活跃期权合约 ID"""
        sql = f"""
        SELECT instrument_id
        FROM {self.TABLE}
        WHERE exchange_id = :exchange_id
          AND status = 1
          AND delist_date >= CURRENT_DATE
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql), {"exchange_id": exchange_id})
                return [row[0] for row in result]
        except Exception:
            # 表可能尚未创建
            return []

    def get_option_meta_map(self, exchange_id: str = None) -> Dict[str, dict]:
        """
        获取期权元数据映射
        :param exchange_id: 交易所代码，None=全部交易所
        :return: {instrument_id: {underlying_symbol, strike_price, contract_type, expiry_date, multiplier, tick_size}}
        """
        if exchange_id:
            sql = f"""
            SELECT instrument_id, underlying_symbol, strike_price, contract_type,
                   expiry_date, multiplier, tick_size
            FROM {self.TABLE}
            WHERE exchange_id = :exchange_id
              AND status = 1
              AND delist_date >= CURRENT_DATE
            """
            params = {"exchange_id": exchange_id}
        else:
            sql = f"""
            SELECT instrument_id, underlying_symbol, strike_price, contract_type,
                   expiry_date, multiplier, tick_size
            FROM {self.TABLE}
            WHERE status = 1
              AND delist_date >= CURRENT_DATE
            """
            params = {}

        mapping = {}
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql), params)
                for row in result:
                    mapping[row[0]] = {
                        'underlying_symbol': row[1],
                        'strike_price': int(float(row[2]) * 10000) if row[2] else 0,
                        'contract_type': row[3],
                        'expiry_date': int(str(row[4]).replace('-', '')) if row[4] else 0,
                        'multiplier': float(row[5]) if row[5] else 1.0,
                        'tick_size': float(row[6]) if row[6] else 0.0001,
                    }
        except Exception:
            pass
        return mapping
