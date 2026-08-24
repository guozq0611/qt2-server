"""
配置查看路由（脱敏）

返回当前 .env 配置，密码等敏感字段脱敏
"""
from fastapi import APIRouter

from core.setting.setting import (
    GATEWAYS, CTP_MD_FRONT_ADDRESS, CTP_SUBSCRIBE_EXCHANGES, CTP_SUBSCRIBE_ASSET_TYPES,
    DB_TYPE, DB_HOST, DB_PORT, DB_USER, DB_DATABASE,
    REDIS_HOST, REDIS_PORT, REDIS_DB,
    ZMQ_BIND_URL, DATA_DIR,
)


router = APIRouter()


def _mask(value: str, visible: int = 2) -> str:
    """脱敏：只保留前 visible 位，其余用 * 替代"""
    if not value or len(value) <= visible:
        return "***"
    return value[:visible] + "***"


@router.get("/")
async def get_config():
    """返回当前配置（脱敏）"""
    return {
        "gateways": GATEWAYS,
        "ctp": {
            "md_front_address": CTP_MD_FRONT_ADDRESS,
            "subscribe_exchanges": CTP_SUBSCRIBE_EXCHANGES,
            "subscribe_asset_types": CTP_SUBSCRIBE_ASSET_TYPES,
        },
        "database": {
            "type": DB_TYPE,
            "host": DB_HOST,
            "port": DB_PORT,
            "user": DB_USER,
            "password": _mask("***"),
            "database": DB_DATABASE,
        },
        "redis": {
            "host": REDIS_HOST,
            "port": REDIS_PORT,
            "password": _mask("***"),
            "db": REDIS_DB,
        },
        "zmq": {
            "bind_url": ZMQ_BIND_URL,
        },
        "data": {
            "dir": DATA_DIR,
        },
    }
