import os
import sys
import datetime
from loguru import logger
from core.common.const import PROJECT_NAME


class LogUtil:
    _is_configured = False

    @classmethod
    def config_logger(cls):
        if cls._is_configured:
            return

        # 1. 移除 loguru 默认的控制台输出（防止重复打印）
        logger.remove()

        # 2. 配置文件输出路径
        file_dir = f"{os.path.expanduser('~')}{os.sep}.{PROJECT_NAME}{os.sep}log"
        os.makedirs(file_dir, exist_ok=True)
        file_name = os.path.join(file_dir, f"log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

        # 3. 添加控制台终端输出 (级别 10 = DEBUG)
        logger.add(sys.stdout, level="DEBUG", format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

        # 4. 添加文件输出 (开启异步 enqueue=True，每天半夜轮转，保留5天)
        logger.add(file_name, level="DEBUG", rotation="00:00", retention="5 days", enqueue=True,
                   format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}")

        cls._is_configured = True

    @staticmethod
    def debug(message: str):
        logger.opt(depth=1).debug(message)

    @staticmethod
    def info(message: str):
        logger.opt(depth=1).info(message)

    @staticmethod
    def warning(message: str):
        logger.opt(depth=1).warning(message)

    @staticmethod
    def error(message: str):
        logger.opt(depth=1).error(message)


# 初始化加载
LogUtil.config_logger()
Logger = LogUtil()
