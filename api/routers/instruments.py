"""
合约列表路由

数据来源：MySQL（future_info / option_info）
"""
from fastapi import APIRouter, Query

from core.util.db_util import get_db_engine
from repository.instrument.future_info_repo import FutureInfoRepo, classify_future
from repository.instrument.option_info_repo import OptionInfoRepo
from core.setting.setting import CTP_SUBSCRIBE_EXCHANGES


router = APIRouter()


@router.get("/future")
async def list_future(
    exchange: str = Query(None, description="交易所过滤"),
    future_type: str = Query(None, description="期货子类型过滤: STOCK_INDEX / BOND / COMMODITY"),
    product_id: str = Query(None, description="品种过滤, 如 IF, CU, SC"),
    active_only: bool = Query(True, description="只返回活跃合约"),
):
    """期货合约列表（含完整信息 + 期货分类）"""
    engine = get_db_engine()
    repo = FutureInfoRepo(engine)

    if active_only:
        instruments = repo.get_active_instruments_detail(exchange)
    else:
        # 不支持 inactive 的 detail 查询，回退到简单列表
        exchanges = [exchange] if exchange else CTP_SUBSCRIBE_EXCHANGES
        instruments = []
        for ex in exchanges:
            for sym in repo.get_active_instruments(ex) or []:
                instruments.append({"symbol": sym, "exchange": ex, "future_type": "COMMODITY"})

    # 过滤
    if future_type:
        instruments = [i for i in instruments if i.get("future_type") == future_type.upper()]
    if product_id:
        instruments = [i for i in instruments if i.get("product_id", "").upper() == product_id.upper()]

    return {"count": len(instruments), "instruments": instruments}


@router.get("/future/products")
async def list_future_products():
    """期货品种列表（用于过滤下拉框）"""
    engine = get_db_engine()
    repo = FutureInfoRepo(engine)
    instruments = repo.get_active_instruments_detail()

    products = {}
    for inst in instruments:
        pid = inst["product_id"]
        if pid not in products:
            products[pid] = {
                "product_id": pid,
                "exchange": inst["exchange"],
                "future_type": inst["future_type"],
                "name": inst["name"][:2] if len(inst["name"]) >= 2 else inst["name"],
                "count": 0,
            }
        products[pid]["count"] += 1

    product_list = sorted(products.values(), key=lambda x: (x["future_type"], x["exchange"], x["product_id"]))
    return {"count": len(product_list), "products": product_list}


@router.get("/option")
async def list_option(
    exchange: str = Query(None, description="交易所过滤"),
    active_only: bool = Query(True, description="只返回活跃合约"),
):
    """期权合约列表（含标的/行权价/类型/到期日等详情）"""
    engine = get_db_engine()
    repo = OptionInfoRepo(engine)

    if active_only:
        instruments = repo.get_active_instruments_detail(exchange)
    else:
        instruments = repo.get_active_instruments_detail(exchange)  # 暂不支持 inactive

    return {"count": len(instruments), "instruments": instruments}


@router.get("/summary")
async def instruments_summary():
    """合约数量汇总（含期货子分类）"""
    engine = get_db_engine()
    repo = FutureInfoRepo(engine)
    instruments = repo.get_active_instruments_detail()

    summary = {
        "future": {},
        "future_by_type": {"STOCK_INDEX": 0, "BOND": 0, "COMMODITY": 0},
        "option": {},
        "total": 0,
    }

    for inst in instruments:
        ex = inst["exchange"]
        summary["future"][ex] = summary["future"].get(ex, 0) + 1
        summary["future_by_type"][inst["future_type"]] += 1
        summary["total"] += 1

    for ex in CTP_SUBSCRIBE_EXCHANGES:
        try:
            option_repo = OptionInfoRepo(engine)
            option_count = len(option_repo.get_active_instruments(ex) or [])
            summary["option"][ex] = option_count
            summary["total"] += option_count
        except Exception:
            summary["option"][ex] = 0

    return summary
