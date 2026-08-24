import os
import platform
from core.util.log_util import Logger

_SYSTEM = platform.system().lower()

if _SYSTEM == "windows":
    import ctypes
else:
    import fcntl


class ProcessUtil:
    """进程级通用工具类"""

    _active_locks = []
    _win_mutex = None

    @classmethod
    def acquire_singleton_lock(cls, job_name: str) -> bool:
        """
        尝试获取单例排他锁
        :param job_name: 任务唯一标识名
        :return: True 表示获取成功，False 表示已有实例在运行
        """
        if _SYSTEM == "windows":
            mutex_name = f"Global\\Qt2Server_{job_name}_Mutex"
            mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)

            if ctypes.windll.kernel32.GetLastError() == 183:
                Logger.warning(f"⚠️ [{job_name}] 获取单例锁失败：检测到已有实例正在运行。")
                return False

            cls._win_mutex = mutex
            return True

        else:
            lock_file = f'/tmp/qt2_server_{job_name}.lock'
            try:
                fp = open(lock_file, 'w')
                fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)

                fp.write(str(os.getpid()))
                fp.flush()
                cls._active_locks.append(fp)

                return True

            except (IOError, OSError):
                Logger.warning(f"⚠️ [{job_name}] 获取单例锁失败：检测到已有实例正在运行。")
                return False
