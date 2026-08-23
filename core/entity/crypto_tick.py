"""
数字货币 Tick 数据（占位）
- 继承 BaseTick，扩展数字货币专用字段
- 未来接入 Binance/OKX 等交易所 WebSocket 时实现
"""
from dataclasses import dataclass
from core.entity.base_tick import BaseTick


@dataclass(slots=True)
class CryptoTickData(BaseTick):
    """
    数字货币 Tick 数据（占位）
    扩展字段待接入具体交易所后补充：
    - 交易所内部交易对 ID
    - 多档深度（通常 20 档）
    - funding rate（永续合约）
    """
    # --- 数字货币专属字段（占位，待实现） ---
    # symbol: str = ''              # 交易所原始交易对, 例: 'BTCUSDT'
    # funding_rate: float = 0.0     # 资金费率（永续合约）
    # mark_price: int = 0           # 标记价格
    # index_price: int = 0          # 指数价格
    pass
