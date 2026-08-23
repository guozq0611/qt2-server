"""
期权 Level1 Tick 数据
- 继承 BaseTick，扩展期权专用字段
- 注意：CTP 行情接口不直接推送 Greeks，Greeks 需要下游用 implied volatility 计算
- 这里预留 Greeks 字段位（默认 0），方便下游消费时填充
"""
from dataclasses import dataclass
from core.entity.base_tick import BaseTick


@dataclass(slots=True)
class OptionLevel1TickData(BaseTick):
    """
    期权 Level1 Tick 数据
    扩展字段说明：
    - Greeks 字段默认 0，CTP 行情不推送，由下游计算后填充
    - 行权价、标的代码用于期权定价与 Greeks 计算
    """
    # --- 期权专属字段 ---
    underlying_symbol: str = ''       # 标的合约代码, 例: 'IF2603'
    strike_price: int = 0             # 行权价（已放大 10000 倍）
    contract_type: str = ''           # 期权类型: 'C' 认购 / 'P' 认沽
    expiry_date: int = 0              # 到期日, 例: 20260320

    # --- Greeks（CTP 不推送，下游计算后填充，这里预留位） ---
    delta: float = 0.0
    gamma: float = 0.0
    vega: float = 0.0
    theta: float = 0.0
    implied_vol: float = 0.0          # 隐含波动率
