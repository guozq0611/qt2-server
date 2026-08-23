"""
CTP 本地库加载器（备用方案）
- 当 openctp_ctp PyPI 包不可用时，切换到本地 .so/.dll 绑定
- 使用方法：在 ctp_md_gateway.py 中把
    from openctp_ctp import thostmduserapi as mdapi
  改为
    from qt2.gateway.ctp.ctp_lib import thostmduserapi as mdapi
"""
import os
import sys
import platform
from pathlib import Path

# 获取当前 ctp_lib 文件夹路径
_CURRENT_DIR = Path(__file__).parent
_SYSTEM = platform.system().lower()

# 根据系统定位到具体存放 .pyd / .dll / .so 的子文件夹
if _SYSTEM == "windows":
    _LIB_PATH = _CURRENT_DIR / "windows"
elif _SYSTEM == "darwin":
    _LIB_PATH = _CURRENT_DIR / "macos"
else:
    _LIB_PATH = _CURRENT_DIR / "linux"

if _LIB_PATH.exists():
    # 1. 解决 Python 找不到模块的问题 (.py, .pyd, .so)
    sys.path.insert(0, str(_LIB_PATH))

    # 2. 解决 Windows 底层 C++ 找不到依赖库的问题 (.dll)
    if _SYSTEM == "windows":
        if hasattr(os, 'add_dll_directory'):
            os.add_dll_directory(str(_LIB_PATH))
        os.environ["PATH"] = str(_LIB_PATH) + os.pathsep + os.environ.get("PATH", "")
    elif _SYSTEM == "linux":
        _current_ld = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = str(_LIB_PATH) + (os.pathsep + _current_ld if _current_ld else "")

    # 3. 核心：在此处显式导入，将其暴露给 ctp_lib 包外部
    try:
        import thostmduserapi
        import thosttraderapi
    except ImportError as e:
        print(f"❌ 严重错误: CTP 底层库加载失败！")
        print(f"📁 搜索路径: {_LIB_PATH}")
        print(f"❌ 错误详情: {e}")
        raise
