"""
股票期权合约信息仓库
- 查询股票 ETF 期权合约清单（SSE/SZSE）
- 查询期权元数据（标的、行权价、类型、到期日），用于填充 StockOptionLevel1TickData
- 股票期权走 CTP 股票期权柜台（openctp_ctpopt），与期货期权是不同的 API
"""
from sqlalchemy import text
from typing import List, Dict


class StockOptionInfoRepo:
    """
    股票期权合约信息仓库

    表结构：stock_option_info（instrument_id, exchange_id, underlying_symbol,
      strike_price, contract_type, expiry_date, multiplier, tick_size, status, delist_date）
    """

    TABLE = 'stock_option_info'

    def __init__(self, engine):
        self.engine = engine

    def get_active_instruments(self, exchange_id: str = 'SSE') -> List[str]:
        """从数据库获取指定交易所的所有活跃股票期权合约 ID"""
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

    def get_active_instruments_detail(self, exchange_id: str = None) -> List[dict]:
        """获取活跃股票期权合约详情（含标的/行权价/类型/到期日等）"""
        if exchange_id:
            sql = f"""
            SELECT instrument_id, exchange_id, instrument_name, underlying_symbol,
                   contract_type, strike_price, multiplier, tick_size,
                   delivery_month, expiry_date, list_date, delist_date
            FROM {self.TABLE}
            WHERE exchange_id = :exchange_id
              AND status = 1
              AND delist_date >= CURRENT_DATE
            ORDER BY underlying_symbol, expiry_date, strike_price
            """
            params = {"exchange_id": exchange_id}
        else:
            sql = f"""
            SELECT instrument_id, exchange_id, instrument_name, underlying_symbol,
                   contract_type, strike_price, multiplier, tick_size,
                   delivery_month, expiry_date, list_date, delist_date
            FROM {self.TABLE}
            WHERE status = 1
              AND delist_date >= CURRENT_DATE
            ORDER BY exchange_id, underlying_symbol, expiry_date, strike_price
            """
            params = {}

        result_list = []
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(text(sql), params)
                for row in rows:
                    result_list.append({
                        "symbol": row[0],
                        "exchange": row[1],
                        "name": row[2],
                        "underlying": row[3],
                        "contract_type": row[4],
                        "strike_price": float(row[5]) if row[5] else 0,
                        "multiplier": float(row[6]) if row[6] else 1,
                        "tick_size": float(row[7]) if row[7] else 0,
                        "delivery_month": row[8],
                        "expiry_date": str(row[9]) if row[9] else None,
                        "list_date": str(row[10]) if row[10] else None,
                        "delist_date": str(row[11]) if row[11] else None,
                    })
        except Exception:
            pass
        return result_list

    def get_option_meta_map(self, exchange_id: str = None) -> Dict[str, dict]:
        """
        获取股票期权元数据映射
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
