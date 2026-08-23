"""
期货 Level1 Tick 数据
- 完全对齐原 quantlab 的 FutureLevel1TickData
- 继承 BaseTick，无额外字段（期货 tick 字段 = 公共字段）
- 用于 CTP 期货行情接收与落盘
"""
from dataclasses import dataclass
from core.entity.base_tick import BaseTick


@dataclass(slots=True)
class FutureLevel1TickData(BaseTick):
    """
    期货 Level1 Tick 数据
    字段与 BaseTick 完全一致，单独定义是为了：
    1. 类型区分（isinstance 判断资产类型）
    2. 未来可能扩展期货专用字段（如结算价、昨结算等）
    """
    pass
