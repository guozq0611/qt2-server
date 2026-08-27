"""
监控路由：系统状态总览 + 行情快照 + ZMQ 状态 + Redis 状态

数据来源：Redis
- qt2:monitor:{asset_type}_sys_health  系统健康指标
- qt2:state:{asset_type}_latest_tick   行情快照
- qt2:monitor:zmq_stats                ZMQ 发布统计
- Redis INFO 命令                      Redis 服务器指标
"""
import json
import re
from fastapi import APIRouter, Query

from core.database.redis.redis_client import RedisClient
from repository.instrument.future_info_repo import classify_future
from core.setting.setting import CTP_SUBSCRIBE_ASSET_TYPES, ZMQ_BIND_URL, REDIS_HOST, REDIS_PORT, REDIS_DB


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


def _extract_product(symbol: str) -> str:
    m = re.match(r'^([a-zA-Z]+)', symbol)
    return m.group(1).upper() if m else ''


def _classify_option(exchange: str) -> str:
    if exchange == 'CFFEX':
        return 'INDEX_OPTION'
    if exchange in ('SSE', 'SZSE'):
        return 'STOCK_OPTION'
    return 'COMMODITY_OPTION'


@router.get("/ticks/{asset_type}")
async def latest_ticks(
    asset_type: str,
    limit: int = Query(100, ge=0),
    future_type: str = Query(None, description="期货分类: STOCK_INDEX / BOND / COMMODITY"),
    option_type: str = Query(None, description="期权分类: INDEX_OPTION / COMMODITY_OPTION / STOCK_OPTION"),
    product_id: str = Query(None, description="品种过滤, 如 IC, IO, AG"),
):
    """获取指定资产类型的最新行情快照

    支持按 future_type / option_type / product_id 过滤，减少前端数据量。
    """
    asset_type = asset_type.lower()
    rc = RedisClient.get_client()
    if rc is None:
        return {"error": "Redis 不可用"}

    state_key = f"qt2:state:{asset_type}_latest_tick"
    raw = rc.hgetall(state_key)
    if not raw:
        return {"asset_type": asset_type, "count": 0, "ticks": []}

    filter_product = product_id.upper() if product_id else None
    ticks = []
    for symbol, json_str in raw.items():
        try:
            tick = json.loads(json_str)
            tick["symbol"] = symbol

            # 品种过滤
            if filter_product:
                if _extract_product(symbol) != filter_product:
                    continue

            # 分类过滤
            if asset_type == 'future' and future_type:
                product = _extract_product(symbol)
                if classify_future(product) != future_type.upper():
                    continue
            if asset_type == 'option' and option_type:
                if _classify_option(tick.get('exchange', '')) != option_type.upper():
                    continue

            ticks.append(tick)
        except json.JSONDecodeError:
            continue

    # 按 update_time 降序排序
    ticks.sort(key=lambda x: (x.get("update_time", ""), x.get("symbol", "")), reverse=True)

    if limit > 0:
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
        ticks.sort(key=lambda x: (x.get("update_time", ""), x.get("symbol", "")), reverse=True)
        if limit > 0:
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


@router.get("/redis")
async def redis_status():
    """Redis 服务器状态监控

    通过 Redis INFO 命令获取服务器指标，
    暴露：版本、运行时间、内存、连接数、命令统计、命中率、qt2 相关 key。
    """
    rc = RedisClient.get_client()
    if rc is None:
        return {"error": "Redis 不可用", "status": "offline"}

    try:
        info = rc.info()
    except Exception as e:
        return {"error": str(e), "status": "error"}

    # 命中率
    hits = info.get("keyspace_hits", 0)
    misses = info.get("keyspace_misses", 0)
    hit_rate = round(hits / (hits + misses) * 100, 2) if (hits + misses) > 0 else 0

    # 运行时间格式化
    uptime_sec = info.get("uptime_in_seconds", 0)
    uptime_days = uptime_sec // 86400
    uptime_hours = (uptime_sec % 86400) // 3600

    # qt2 相关 key 详情
    qt2_keys = []
    try:
        all_keys = rc.keys("qt2:*")
        for key in all_keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            key_type = rc.type(key).decode()
            detail = {"key": key_str, "type": key_type}
            if key_type == "hash":
                detail["field_count"] = rc.hlen(key)
            elif key_type == "string":
                detail["size"] = len(rc.get(key) or b"")
            elif key_type == "list":
                detail["length"] = rc.llen(key)
            qt2_keys.append(detail)
    except Exception:
        pass

    result = {
        "status": "online",
        "host": f"{REDIS_HOST}:{REDIS_PORT}",
        "db": REDIS_DB,
        "version": info.get("redis_version", "unknown"),
        "uptime_days": uptime_days,
        "uptime_hours": uptime_hours,
        "uptime_seconds": uptime_sec,
        "connected_clients": info.get("connected_clients", 0),
        "total_connections_received": info.get("total_connections_received", 0),
        "used_memory": info.get("used_memory_human", "0"),
        "used_memory_peak": info.get("used_memory_peak_human", "0"),
        "used_memory_rss": info.get("used_memory_rss_human", "0"),
        "total_commands_processed": info.get("total_commands_processed", 0),
        "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
        "keyspace_hits": hits,
        "keyspace_misses": misses,
        "hit_rate": hit_rate,
        "evicted_keys": info.get("evicted_keys", 0),
        "expired_keys": info.get("expired_keys", 0),
        "db_size": info.get(f"db{REDIS_DB}", {}).get("keys", 0) if isinstance(info.get(f"db{REDIS_DB}"), dict) else 0,
        "db_expires": info.get(f"db{REDIS_DB}", {}).get("expires", 0) if isinstance(info.get(f"db{REDIS_DB}"), dict) else 0,
        "qt2_keys": qt2_keys,
    }

    return result
