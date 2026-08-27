"""
WebSocket 行情推送
- 一个全局 ZMQ SUB 接收所有 TICK.* 二进制数据
- 提取 symbol 后从 Redis 读取 JSON 快照
- 按客户端订阅的 asset_type / future_type / option_type / product_id 过滤推送
- 用于替代前端 1 秒轮询
"""
import asyncio
import json
import threading
import time
from typing import List, Optional, Set

import zmq
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from core.database.redis.redis_client import RedisClient
from core.setting.setting import ZMQ_BIND_URL
from core.util.log_util import Logger
from repository.instrument.future_info_repo import classify_future


router = APIRouter()

# 客户端连接：维护 WebSocket 与过滤条件
class _Client:
    def __init__(self, ws: WebSocket, asset_type: str, future_type: Optional[str],
                 option_type: Optional[str], product_id: Optional[str]):
        self.ws = ws
        self.asset_type = asset_type.upper()
        self.future_type = future_type.upper() if future_type else None
        self.option_type = option_type.upper() if option_type else None
        self.product_id = product_id.upper() if product_id else None


_clients: Set[_Client] = set()
_loop: Optional[asyncio.AbstractEventLoop] = None
_queue: asyncio.Queue = asyncio.Queue()


def _classify_option(exchange: str) -> str:
    if exchange == 'CFFEX':
        return 'INDEX_OPTION'
    if exchange in ('SSE', 'SZSE'):
        return 'STOCK_OPTION'
    return 'COMMODITY_OPTION'


def _extract_product(symbol: str) -> str:
    import re
    m = re.match(r'^([a-zA-Z]+)', symbol)
    return m.group(1).upper() if m else ''


def _start_zmq_subscriber():
    """在后台线程启动 ZMQ SUB，所有消息放入 asyncio 队列"""
    # 将 bind_url 里的通配符替换为本地回环，用于连接
    connect_url = ZMQ_BIND_URL.replace('*', '127.0.0.1')
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.setsockopt(zmq.RCVHWM, 5000)
    socket.setsockopt(zmq.SUBSCRIBE, b'TICK.')
    try:
        socket.connect(connect_url)
        Logger.info(f"WebSocket ZMQ Subscriber connected to {connect_url}")
    except Exception as e:
        Logger.error(f"WebSocket ZMQ Subscriber failed to connect to {connect_url}: {e}")
        return

    def run():
        while True:
            try:
                topic_bytes, raw_bytes = socket.recv_multipart()
                topic = topic_bytes.decode('utf-8', errors='replace')
                parts = topic.split('.')
                if len(parts) < 3:
                    continue
                asset_type = parts[1].upper()
                product_id = parts[2].upper()
                # 二进制前 16 字节是 instrument_id
                symbol = raw_bytes[:16].split(b'\x00')[0].decode('utf-8', errors='replace')
                if _loop is not None:
                    _loop.call_soon_threadsafe(_queue.put_nowait, (asset_type, product_id, symbol))
            except Exception as e:
                Logger.error(f"WebSocket ZMQ subscriber error: {e}")
                time.sleep(0.1)

    t = threading.Thread(target=run, daemon=True)
    t.start()


async def _broadcast_loop():
    """从队列取 ZMQ 消息，读取 Redis，推送给匹配的客户端"""
    rc = RedisClient.get_client()
    while True:
        try:
            asset_type, product_id, symbol = await _queue.get()
            if not _clients:
                continue
            if rc is None:
                continue

            key = f"qt2:state:{asset_type.lower()}_latest_tick"
            raw = rc.hget(key, symbol)
            if not raw:
                continue

            try:
                tick = json.loads(raw)
            except json.JSONDecodeError:
                continue

            tick['symbol'] = symbol
            tick['product_id'] = product_id

            # 广播给匹配客户端
            for client in list(_clients):
                if client.asset_type != asset_type:
                    continue
                if client.product_id and client.product_id != product_id:
                    continue

                # 分类过滤
                if asset_type == 'FUTURE' and client.future_type:
                    if classify_future(product_id) != client.future_type:
                        continue
                if asset_type == 'OPTION' and client.option_type:
                    if _classify_option(tick.get('exchange', '')) != client.option_type:
                        continue

                try:
                    await client.ws.send_json({
                        'event': 'tick',
                        'asset_type': asset_type,
                        'product_id': product_id,
                        'tick': tick,
                    })
                except Exception:
                    _clients.discard(client)
        except Exception as e:
            Logger.error(f"WebSocket broadcast error: {e}")


def init_websocket(app_loop: asyncio.AbstractEventLoop):
    global _loop
    _loop = app_loop
    _start_zmq_subscriber()
    asyncio.create_task(_broadcast_loop())


@router.websocket("/ws/ticks/{asset_type}")
async def tick_websocket(
    websocket: WebSocket,
    asset_type: str,
    future_type: Optional[str] = Query(None),
    option_type: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
):
    """WebSocket 行情推送

    连接示例: /api/ws/ticks/future?product_id=IH
              /api/ws/ticks/option?option_type=INDEX_OPTION&product_id=IO
    """
    client = _Client(websocket, asset_type, future_type, option_type, product_id)
    _clients.add(client)
    try:
        await websocket.accept()
        # 等待客户端主动断开
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data) if data else {}
            # 可扩展：客户端发送订阅变更消息
            if msg.get('action') == 'ping':
                await websocket.send_json({'event': 'pong'})
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(client)
