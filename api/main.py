import asyncio

"""
qt2-server 监控 API（FastAPI）

提供前端 UI 所需的 REST API：
- 系统状态总览（Redis 监控数据）
- 行情快照（Redis latest_tick）
- 合约列表（MySQL）
- 落盘文件列表
- 配置查看（脱敏）

同时托管前端静态文件（frontend/dist），生产环境无需独立 Nginx。
"""
import os
import sys

# 确保项目根目录在 sys.path 中
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.routers import monitor, instruments, files, config
from api import websocket as ws_module


app = FastAPI(
    title="qt2-server 监控 API",
    description="行情接收引擎监控与管理接口",
    version="1.0.0",
)

# CORS（允许前端 dev server 跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api")
async def api_root():
    return {"service": "qt2-server", "status": "ok", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "ok"}


# 注册路由
app.include_router(monitor.router, prefix="/api/monitor", tags=["监控"])
app.include_router(instruments.router, prefix="/api/instruments", tags=["合约"])
app.include_router(files.router, prefix="/api/files", tags=["文件"])
app.include_router(config.router, prefix="/api/config", tags=["配置"])
app.include_router(ws_module.router, prefix="/api/ws", tags=["WebSocket"])


# WebSocket 行情广播初始化
@app.on_event("startup")
async def startup_websocket():
    ws_module.init_websocket(asyncio.get_event_loop())


# ===== 前端静态文件托管 =====
# 如果 frontend/dist 存在，则托管前端（生产模式）
_FRONTEND_DIST = os.path.join(_PROJECT_ROOT, "frontend", "dist")
if os.path.isdir(_FRONTEND_DIST):
    # 挂载静态资源目录（/assets/*）
    _ASSETS_DIR = os.path.join(_FRONTEND_DIST, "assets")
    if os.path.isdir(_ASSETS_DIR):
        app.mount("/assets", StaticFiles(directory=_ASSETS_DIR), name="assets")

    # SPA fallback：所有非 /api、非 /health 的请求返回 index.html
    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        # 排除 API 路径（已被上面的路由处理）
        if full_path.startswith("api") or full_path.startswith("health"):
            return {"detail": "Not Found"}
        index_path = os.path.join(_FRONTEND_DIST, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        return {"detail": "Frontend not built"}

