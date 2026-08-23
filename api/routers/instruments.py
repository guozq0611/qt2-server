"""
合约列表路由

数据来源：MySQL（future_info / option_info）
"""
from fastapi import APIRouter, Query

from core.util.db_util import get_db_engine
from repository.instrument.future_info_repo import FutureInfoRepo
from repository.instrument.option_info_repo import OptionInfoRepo
from core.setting.setting import CTP_SUBSCRIBE_EXCHANGES


router = APIRouter()


@router.get("/future")
async def list_future(
    exchange: str = Query(None, description="交易所过滤"),
    active_only: bool = Query(True, description="只返回活跃合约"),
):
    """期货合约列表"""
    engine = get_db_engine()
    repo = FutureInfoRepo(engine)

    exchanges = [exchange] if exchange else CTP_SUBSCRIBE_EXCHANGES
    result = []

    for ex in exchanges:
        instruments = repo.get_active_instruments(ex) if active_only else repo.get_all_instruments(ex)
        if instruments:
            for symbol in instruments:
                result.append({"symbol": symbol, "exchange": ex, "asset_type": "FUTURE"})

    return {"count": len(result), "instruments": result}


@router.get("/option")
async def list_option(
    exchange: str = Query(None, description="交易所过滤"),
    active_only: bool = Query(True, description="只返回活跃合约"),
):
    """期权合约列表"""
    engine = get_db_engine()
    repo = OptionInfoRepo(engine)

    exchanges = [exchange] if exchange else CTP_SUBSCRIBE_EXCHANGES
    result = []

    for ex in exchanges:
        try:
            instruments = repo.get_active_instruments(ex) if active_only else repo.get_all_instruments(ex)
            if instruments:
                for symbol in instruments:
                    result.append({"symbol": symbol, "exchange": ex, "asset_type": "OPTION"})
        except Exception:
            # option_info 表可能不存在
            continue

    return {"count": len(result), "instruments": result}


@router.get("/summary")
async def instruments_summary():
    """合约数量汇总"""
    engine = get_db_engine()
    future_repo = FutureInfoRepo(engine)

    summary = {"future": {}, "option": {}, "total": 0}

    for ex in CTP_SUBSCRIBE_EXCHANGES:
        future_count = len(future_repo.get_active_instruments(ex) or [])
        summary["future"][ex] = future_count
        summary["total"] += future_count

        try:
            option_repo = OptionInfoRepo(engine)
            option_count = len(option_repo.get_active_instruments(ex) or [])
            summary["option"][ex] = option_count
            summary["total"] += option_count
        except Exception:
            summary["option"][ex] = 0

    return summary
