"""
合约列表路由

数据来源：MySQL（future_info / option_info）
"""
import re
from fastapi import APIRouter, Query

from core.util.db_util import get_db_engine
from repository.instrument.future_info_repo import FutureInfoRepo, classify_future
from repository.instrument.option_info_repo import OptionInfoRepo
from repository.instrument.stock_option_info_repo import StockOptionInfoRepo
from core.setting.setting import CTP_SUBSCRIBE_EXCHANGES


router = APIRouter()

# 期权分类
OPTION_TYPE_LABELS = {
    'INDEX_OPTION': '股指期权',
    'COMMODITY_OPTION': '商品期权',
    'STOCK_OPTION': '股票期权',
}

OPTION_TYPE_COLORS = {
    'INDEX_OPTION': 'red',
    'COMMODITY_OPTION': 'emerald',
    'STOCK_OPTION': 'blue',
}


def classify_option(exchange_id: str) -> str:
    """根据交易所对期权分类"""
    if exchange_id == 'CFFEX':
        return 'INDEX_OPTION'
    elif exchange_id in ('SSE', 'SZSE'):
        return 'STOCK_OPTION'
    else:
        return 'COMMODITY_OPTION'


def extract_option_product(symbol: str) -> str:
    """从期权合约代码提取品种代码（大写）
    CFFEX: IO2603-C-3900 -> IO
    SHFE:  ag2610c10000  -> AG
    """
    m = re.match(r'^([a-zA-Z]+)', symbol)
    return m.group(1).upper() if m else ''


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
    option_type: str = Query(None, description="期权分类: INDEX_OPTION / COMMODITY_OPTION / STOCK_OPTION"),
    active_only: bool = Query(True, description="只返回活跃合约"),
):
    """期权合约列表（含标的/行权价/类型/到期日等详情 + 期权分类）"""
    engine = get_db_engine()
    repo = OptionInfoRepo(engine)

    if active_only:
        instruments = repo.get_active_instruments_detail(exchange)
    else:
        instruments = repo.get_active_instruments_detail(exchange)

    # 加期权分类和品种代码
    for inst in instruments:
        inst['option_type'] = classify_option(inst['exchange'])
        inst['product_id'] = extract_option_product(inst['symbol'])

    # 按分类过滤
    if option_type:
        instruments = [i for i in instruments if i['option_type'] == option_type.upper()]

    return {"count": len(instruments), "instruments": instruments}


@router.get("/option/products")
async def list_option_products():
    """期权品种列表（用于过滤下拉框）"""
    engine = get_db_engine()
    repo = OptionInfoRepo(engine)
    instruments = repo.get_active_instruments_detail()

    products = {}
    for inst in instruments:
        pid = extract_option_product(inst['symbol'])
        otype = classify_option(inst['exchange'])
        if pid not in products:
            products[pid] = {
                "product_id": pid,
                "exchange": inst['exchange'],
                "option_type": otype,
                "name": inst.get('name', '')[:4],
                "count": 0,
            }
        products[pid]["count"] += 1

    product_list = sorted(products.values(), key=lambda x: (x['option_type'], x['exchange'], x['product_id']))
    return {"count": len(product_list), "products": product_list}


# ==========================================================
# 股票期权（ETF 期权，SSE/SZSE，走 CTP 股票期权柜台）
# ==========================================================

def extract_stock_option_underlying(symbol: str) -> str:
    """从股票期权合约代码提取标的证券代码
    例: 510050C2603M02500 -> 510050
    """
    m = re.match(r'^(\d{6})', symbol)
    return m.group(1) if m else ''


@router.get("/stock-option")
async def list_stock_option(
    exchange: str = Query(None, description="交易所过滤: SSE / SZSE"),
    underlying: str = Query(None, description="标的证券代码过滤, 如 510050"),
    active_only: bool = Query(True, description="只返回活跃合约"),
):
    """股票期权合约列表（含标的/行权价/类型/到期日等详情）"""
    engine = get_db_engine()
    repo = StockOptionInfoRepo(engine)
    instruments = repo.get_active_instruments_detail(exchange)

    # 加标的代码
    for inst in instruments:
        inst['underlying_code'] = extract_stock_option_underlying(inst['symbol'])

    # 按标的过滤
    if underlying:
        instruments = [i for i in instruments if i['underlying_code'] == underlying]

    return {"count": len(instruments), "instruments": instruments}


@router.get("/stock-option/underlyings")
async def list_stock_option_underlyings():
    """股票期权标的列表（用于过滤下拉框）"""
    engine = get_db_engine()
    repo = StockOptionInfoRepo(engine)
    instruments = repo.get_active_instruments_detail()

    underlyings = {}
    for inst in instruments:
        code = extract_stock_option_underlying(inst['symbol'])
        if code not in underlyings:
            underlyings[code] = {
                "underlying": code,
                "exchange": inst['exchange'],
                "name": inst.get('underlying', '') or code,
                "count": 0,
            }
        underlyings[code]["count"] += 1

    underlying_list = sorted(underlyings.values(), key=lambda x: (x['exchange'], x['underlying']))
    return {"count": len(underlying_list), "underlyings": underlying_list}


@router.get("/summary")
async def instruments_summary():
    """合约数量汇总（含期货子分类 + 期权子分类 + 股票期权）"""
    engine = get_db_engine()
    repo = FutureInfoRepo(engine)
    instruments = repo.get_active_instruments_detail()

    summary = {
        "future": {},
        "future_by_type": {"STOCK_INDEX": 0, "BOND": 0, "COMMODITY": 0},
        "option": {},
        "option_by_type": {"INDEX_OPTION": 0, "COMMODITY_OPTION": 0, "STOCK_OPTION": 0},
        "stock_option": {},
        "stock_option_total": 0,
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
            summary["option_by_type"][classify_option(ex)] += option_count
            summary["total"] += option_count
        except Exception:
            summary["option"][ex] = 0

    # 股票期权
    try:
        stock_option_repo = StockOptionInfoRepo(engine)
        for ex in ['SSE', 'SZSE']:
            count = len(stock_option_repo.get_active_instruments(ex) or [])
            summary["stock_option"][ex] = count
            summary["stock_option_total"] += count
            summary["total"] += count
    except Exception:
        summary["stock_option"] = {"SSE": 0, "SZSE": 0}

    return summary
