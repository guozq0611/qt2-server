"""
qt2-server 监控 API 启动入口

用法：
  python run/run_api.py                    # 默认 0.0.0.0:8000
  python run/run_api.py --port 8001        # 自定义端口
  python run/run_api.py --reload           # 开发模式热重载
"""
import sys
import os
import argparse

# 确保项目根目录在 sys.path 中
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def main():
    parser = argparse.ArgumentParser(description="qt2-server 监控 API")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    parser.add_argument("--reload", action="store_true", help="热重载（开发模式）")
    args = parser.parse_args()

    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
