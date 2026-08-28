"""
统一配置入口
- 通过 .env 文件加载配置（使用 python-dotenv 自动查找项目根的 .env）
- 参照 dduck-quant 的方式，用 os.getenv 暴露常量，各模块直接 import 使用
- 列表类配置用逗号分隔，通过 _parse_list 辅助解析
"""
import os
from dotenv import load_dotenv, find_dotenv

# 自动向上寻找 .env 文件并加载到环境变量中
# 使用 find_dotenv() 即使在子目录下跑脚本，也能精准找到根目录的 .env
load_dotenv(find_dotenv())


def _parse_list(value: str, default: list) -> list:
    """将逗号分隔的字符串解析为列表，空值返回 default"""
    if not value or not value.strip():
        return default
    return [item.strip() for item in value.split(',') if item.strip()]


# ==========================================================
# 1. 行情网关
# ==========================================================
GATEWAYS = _parse_list(os.getenv("GATEWAYS", "ctp"), ["ctp"])

# ==========================================================
# 2. CTP 行情配置
# ==========================================================
CTP_MD_FRONT_ADDRESS = os.getenv("CTP_MD_FRONT_ADDRESS", "tcp://101.231.162.58:41213")
CTP_SUBSCRIBE_EXCHANGES = _parse_list(
    os.getenv("CTP_SUBSCRIBE_EXCHANGES", "CFFEX,SHFE,DCE,CZCE,INE,GFEX"),
    ["CFFEX", "SHFE", "DCE", "CZCE", "INE", "GFEX"],
)
CTP_SUBSCRIBE_ASSET_TYPES = _parse_list(
    os.getenv("CTP_SUBSCRIBE_ASSET_TYPES", "FUTURE"),
    ["FUTURE"],
)

# ==========================================================
# 2.1 CTP 股票期权行情配置（openctp_ctpopt，独立柜台）
# ==========================================================
# 股票期权走 CTP 股票期权柜台，与期货柜台是不同的前置地址和 API
# 招商期货股票期权生产环境行情前置
CTP_STOCK_OPTION_MD_FRONT_ADDRESS = os.getenv(
    "CTP_STOCK_OPTION_MD_FRONT_ADDRESS", "tcp://180.166.65.115:61213"
)
CTP_SUBSCRIBE_STOCK_OPTION_EXCHANGES = _parse_list(
    os.getenv("CTP_SUBSCRIBE_STOCK_OPTION_EXCHANGES", "SSE,SZSE"),
    ["SSE", "SZSE"],
)

# ==========================================================
# 3. 数据库（合约信息、交易日历）
#    支持: mysql / postgres / ob(OceanBase, 兼容 MySQL 协议)
# ==========================================================
DB_TYPE = os.getenv("DB_TYPE", "mysql").lower()
DB_HOST = os.getenv("DB_HOST", "")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_DATABASE = os.getenv("DB_DATABASE", "")

# 向后兼容：如果 DB_HOST 为空但 MYSQL_HOST 有值，则回退到旧变量
if not DB_HOST:
    DB_HOST = os.getenv("MYSQL_HOST", "")
    DB_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    DB_USER = os.getenv("MYSQL_USER", "")
    DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    DB_DATABASE = os.getenv("MYSQL_DATABASE", "")

# ==========================================================
# 4. Redis（监控上报、最新行情快照）
# ==========================================================
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# ==========================================================
# 5. ZeroMQ 行情广播
# ==========================================================
ZMQ_BIND_URL = os.getenv("ZMQ_BIND_URL", "tcp://*:5555")

# ==========================================================
# 6. 落盘根目录（相对于项目根，也可填绝对路径）
# ==========================================================
DATA_DIR = os.getenv("DATA_DIR", "data/raw")

# ==========================================================
# 7. UI 品牌配置
# ==========================================================
APP_BRAND = os.getenv("APP_BRAND", "Alan Intelligent Technology")

# ==========================================================
# 8. Tushare 数据源（基础数据同步：期货合约信息、交易日历）
# ==========================================================
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "")
