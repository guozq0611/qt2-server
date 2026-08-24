"""
监控路由：系统状态总览 + 行情快照 + ZMQ 状态

数据来源：Redis
- qt2:monitor:{asset_type}_sys_health  系统健康指标
- qt2:state:{asset_type}_latest_tick   行情快照
- qt2:monitor:zmq_stats                ZMQ 发布统计
"""
import json
from fastapi import APIRouter

from core.database.redis.redis_client import RedisClient
from core.setting.setting import CTP_SUBSCRIBE_ASSET_TYPES, ZMQ_BIND_URL


router = APIRouter()

# 支持的资产类型（从配置读取）
ASSET_TYPES = [t.lower() for t in CTP_SUBSCRIBE_ASSET_TYPES]


@router.get("/overview")
async def overview():
    """系统状态总览：所有资产类型的录制器健康指标"""
    rc = RedisClient.get_client()
    if rc is None:
        return {"error": "Redis 不可用"}

    result = {"recorders": {}, "redis_ok": True}

    for asset_type in ASSET_TYPES:
        sys_key = f"qt2:monitor:{asset_type}_sys_health"
        data = rc.hgetall(sys_key)
        if data:
            result["recorders"][asset_type] = {
                "status": data.get("status", "unknown"),
                "heartbeat": int(data.get("heartbeat", 0)),
                "queue_size": int(data.get("queue_size", 0)),
                "total_processed": int(data.get("total_processed", 0)),
                "last_update": data.get("last_update", ""),
            }
        else:
            result["recorders"][asset_type] = {
                "status": "offline",
                "heartbeat": 0,
                "queue_size": 0,
                "total_processed": 0,
                "last_update": "",
            }

    return result


@router.get("/ticks/{asset_type}")
async def latest_ticks(asset_type: str, limit: int = 100):
    """获取指定资产类型的最新行情快照"""
    asset_type = asset_type.lower()
    rc = RedisClient.get_client()
    if rc is None:
        return {"error": "Redis 不可用"}

    state_key = f"qt2:state:{asset_type}_latest_tick"
    raw = rc.hgetall(state_key)
    if not raw:
        return {"asset_type": asset_type, "count": 0, "ticks": []}

    ticks = []
    for symbol, json_str in raw.items():
        try:
            tick = json.loads(json_str)
            tick["symbol"] = symbol
            ticks.append(tick)
        except json.JSONDecodeError:
            continue

    # 按 last_price 或 symbol 排序，限制返回数量
    ticks = ticks[:limit]

    return {"asset_type": asset_type, "count": len(ticks), "ticks": ticks}


@router.get("/ticks")
async def all_latest_ticks(limit: int = 50):
    """获取所有资产类型的最新行情快照"""
    result = {}
    for asset_type in ASSET_TYPES:
        state_key = f"qt2:state:{asset_type}_latest_tick"
        rc = RedisClient.get_client()
        if rc is None:
            continue
        raw = rc.hgetall(state_key)
        if not raw:
            result[asset_type] = {"count": 0, "ticks": []}
            continue

        ticks = []
        for symbol, json_str in raw.items():
            try:
                tick = json.loads(json_str)
                tick["symbol"] = symbol
                ticks.append(tick)
            except json.JSONDecodeError:
                continue
        ticks = ticks[:limit]
        result[asset_type] = {"count": len(ticks), "ticks": ticks}

    return result


@router.get("/zmq")
async def zmq_status():
    """ZMQ 发布者状态监控

    通过 ZMQ socket monitor 追踪 SUB 客户端的连接/断开事件，
    暴露：连接数、发布统计、主题列表、连接事件日志。
    """
    rc = RedisClient.get_client()
    if rc is None:
        return {"error": "Redis 不可用"}

    # 从 Redis 读取 ZMQ 统计
    zmq_key = "qt2:monitor:zmq_stats"
    data = rc.hgetall(zmq_key)

    # 从配置读取静态信息
    result = {
        "bind_url": ZMQ_BIND_URL,
        "socket_type": "PUB",
        "hwm": 2000,
        "status": "unknown",
        "total_published": 0,
        "topics": [],
        "publish_rate": 0,
        "last_publish_time": "",
        "subscriber_count": 0,
        "total_connections": 0,
        "total_disconnections": 0,
        "connection_events": [],
        "note": "subscriber_count 通过 ZMQ socket monitor 追踪 ACCEPTED/DISCONNECTED 事件",
    }

    if data:
        result["status"] = data.get("status", "unknown")
        result["total_published"] = int(data.get("total_published", 0))
        result["last_publish_time"] = data.get("last_publish_time", "")
        topics_str = data.get("topics", "")
        if topics_str:
            result["topics"] = topics_str.split(",")
        try:
            result["publish_rate"] = float(data.get("publish_rate", 0))
        except (ValueError, TypeError):
            result["publish_rate"] = 0

        result["subscriber_count"] = int(data.get("subscriber_count", 0))
        result["total_connections"] = int(data.get("total_connections", 0))
        result["total_disconnections"] = int(data.get("total_disconnections", 0))

        events_str = data.get("connection_events", "")
        if events_str:
            try:
                result["connection_events"] = json.loads(events_str)
            except json.JSONDecodeError:
                result["connection_events"] = []

    return result
