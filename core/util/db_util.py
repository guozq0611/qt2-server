"""
数据库引擎工厂
支持 DB_TYPE: mysql / postgres / ob(OceanBase)
- mysql/ob: 使用 pymysql 驱动，mysql+pymysql:// 连接串
- postgres: 使用 psycopg2 驱动，postgresql+psycopg2:// 连接串
"""
from sqlalchemy import create_engine

from core.setting.setting import DB_TYPE, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE

_db_engine = None


def _build_connection_string() -> str:
    """根据 DB_TYPE 构建 SQLAlchemy 连接串"""
    if DB_TYPE in ("mysql", "ob"):
        # OceanBase 兼容 MySQL 协议，用 pymysql 驱动
        return f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}"
    elif DB_TYPE == "postgres":
        return f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}"
    else:
        raise ValueError(f"不支持的 DB_TYPE: {DB_TYPE}，可选: mysql / postgres / ob")


def get_db_engine(database_name=''):
    global _db_engine
    if _db_engine is not None:
        return _db_engine

    if database_name is None or database_name == '':
        database_name = DB_DATABASE

    db_link = _build_connection_string()
    # 如果指定了其他库名，替换连接串中的库名
    if database_name != DB_DATABASE:
        # 重新拼接（库名在最后）
        if DB_TYPE in ("mysql", "ob"):
            db_link = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{database_name}"
        elif DB_TYPE == "postgres":
            db_link = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{database_name}"

    _db_engine = create_engine(
        db_link,
        echo=False,
        max_overflow=10,
        pool_size=10,
        pool_pre_ping=True,        # 取连接前发 ping，自动丢弃失效连接
        pool_recycle=3600,         # 连接最大存活 1 小时
        pool_reset_on_return=None,
    )
    return _db_engine
