from enum import Enum

PROJECT_NAME = 'qt2-server'

# 价格和成交额的放大倍数, 用于将 ClickHouse 的 Int64 转换为浮点数
PRICE_MULTIPLIER = 10000.0
TURNOVER_MULTIPLIER = 100.0


class AssetType(Enum):
    """资产类型枚举"""
    FUTURE = 'future'
    OPTION = 'option'
    STOCK = 'stock'
