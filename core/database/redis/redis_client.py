"""
Redis 客户端单例工具类（精简版）
- 移除了原 quantlab 中的 stream_chat（LLM 专用）等无关方法
- 只保留行情监控需要的：set_value / hset_mapping / expire_key / get_client
"""
import redis
import json
from typing import Any, Dict, Optional

from core.setting.setting import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB
from core.util.log_util import Logger


class RedisClient:
    """
    Redis 客户端单例工具类
    特性：全局连接池、自动重连、断网熔断保护、常用高频操作封装
    """
    _instance = None
    _pool = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisClient, cls).__new__(cls)
            cls._instance._init_pool()
        return cls._instance

    def _init_pool(self):
        """初始化全局连接池"""
        try:
            self._pool = redis.ConnectionPool(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                db=REDIS_DB,
                decode_responses=True,
                socket_timeout=3,
                socket_connect_timeout=3,
                max_connections=50
            )
            self._client = redis.Redis(connection_pool=self._pool)

            self._client.ping()
            Logger.info(f"Redis client initialized successfully connected to {REDIS_HOST}:{REDIS_PORT}/db{REDIS_DB}")

        except Exception as e:
            Logger.error(f"Failed to connect to Redis: {e}")
            self._client = None

    @classmethod
    def get_client(cls) -> Optional[redis.Redis]:
        """暴露原生客户端实例，供外部进行 Pipeline 或复杂操作"""
        return cls()._client

    @classmethod
    def set_value(cls, key: str, value: Any, ex: int = None) -> bool:
        """写入普通键值对 (支持设置过期时间，秒)"""
        client = cls.get_client()
        if not client:
            return False
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            return client.set(name=key, value=value, ex=ex)
        except Exception as e:
            Logger.error(f"Redis SET error on key {key}: {e}")
            return False

    @classmethod
    def hset_mapping(cls, name: str, mapping: Dict[str, Any]) -> bool:
        """
        [高频核心] 极速覆盖写入 Hash 字典
        用途：用于更新系统健康状态 (quant:monitor:sys_health) 或 全市场最新行情快照
        """
        client = cls.get_client()
        if not client:
            return False
        try:
            return client.hset(name, mapping=mapping)
        except Exception:
            return False

    @classmethod
    def hget_all(cls, name: str) -> Dict[str, str]:
        """获取 Hash 字典的所有内容"""
        client = cls.get_client()
        if not client:
            return {}
        try:
            return client.hgetall(name)
        except Exception as e:
            Logger.error(f"Redis HGETALL error on hash {name}: {e}")
            return {}

    @classmethod
    def expire_key(cls, key: str, seconds: int) -> bool:
        """设置 Key 的过期时间 (常用于心跳/看门狗机制)"""
        client = cls.get_client()
        if not client:
            return False
        try:
            return client.expire(key, seconds)
        except Exception:
            return False


redis_util = RedisClient()
