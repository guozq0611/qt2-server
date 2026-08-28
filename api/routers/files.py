"""
落盘文件路由

列出 data/raw 下的 bin 文件，支持按目录浏览：
- current/    当前交易日实时写入
- YYYYMMDD/   历史归档（盘后自动归档）
"""
import os
import glob
from datetime import datetime
from fastapi import APIRouter, Query

from core.setting.setting import DATA_DIR


router = APIRouter()


# bin 文件每条记录的字节数
RECORD_SIZE = {
    "future": 160,
    "option": 230,
    "stock_option": 470,
}


def _scan_dir(dir_path: str, asset_type: str) -> list:
    """扫描目录下的 bin 文件，返回文件信息列表"""
    if not os.path.isdir(dir_path):
        return []

    record_size = RECORD_SIZE.get(asset_type, 160)
    files = glob.glob(os.path.join(dir_path, "*.bin"))
    files.sort(key=lambda f: os.path.getmtime(f), reverse=True)

    result = []
    for fpath in files:
        fname = os.path.basename(fpath)
        fsize = os.path.getsize(fpath)
        mtime = datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%Y-%m-%d %H:%M:%S")
        record_count = fsize // record_size if fsize > 0 else 0

        result.append({
            "filename": fname,
            "size_bytes": fsize,
            "size_mb": round(fsize / 1024 / 1024, 2),
            "record_count": record_count,
            "modified": mtime,
        })

    return result


@router.get("/list")
async def list_files(
    asset_type: str = Query("future", description="资产类型: future / option"),
    directory: str = Query("current", description="目录: current 或 YYYYMMDD"),
):
    """列出落盘的 bin 文件

    - directory=current: 当前交易日实时写入的文件
    - directory=YYYYMMDD: 历史归档目录
    """
    base_dir = os.path.join(DATA_DIR, asset_type, "level1", "tick")
    if not os.path.isdir(base_dir):
        return {"asset_type": asset_type, "directory": directory, "count": 0, "files": []}

    # 安全检查：directory 只允许 current 或 8 位数字
    if directory != "current" and not (len(directory) == 8 and directory.isdigit()):
        return {"error": "invalid directory"}

    target_dir = os.path.join(base_dir, directory)
    files = _scan_dir(target_dir, asset_type)

    return {"asset_type": asset_type, "directory": directory, "count": len(files), "files": files}


@router.get("/directories")
async def list_directories(
    asset_type: str = Query("future", description="资产类型: future / option"),
):
    """列出可用的目录（current + 历史归档日期）"""
    base_dir = os.path.join(DATA_DIR, asset_type, "level1", "tick")
    if not os.path.isdir(base_dir):
        return {"asset_type": asset_type, "directories": []}

    dirs = []
    for name in sorted(os.listdir(base_dir), reverse=True):
        full = os.path.join(base_dir, name)
        if not os.path.isdir(full):
            continue
        if name == "current":
            dirs.append({"name": name, "label": "当前交易日", "is_current": True})
        elif len(name) == 8 and name.isdigit():
            dirs.append({"name": name, "label": name, "is_current": False})

    # current 排最前
    dirs.sort(key=lambda d: not d["is_current"])
    return {"asset_type": asset_type, "directories": dirs}


@router.get("/stats")
async def files_stats():
    """落盘文件统计（current + 所有历史目录）"""
    stats = {}

    for asset_type in ["future", "option", "stock_option"]:
        base_dir = os.path.join(DATA_DIR, asset_type, "level1", "tick")
        if not os.path.isdir(base_dir):
            stats[asset_type] = {"file_count": 0, "total_size_mb": 0, "total_records": 0}
            continue

        record_size = RECORD_SIZE.get(asset_type, 160)
        # 扫描所有子目录（包括 current 和 YYYYMMDD）
        all_files = glob.glob(os.path.join(base_dir, "**", "*.bin"), recursive=True)
        total_size = sum(os.path.getsize(f) for f in all_files)
        total_records = total_size // record_size

        stats[asset_type] = {
            "file_count": len(all_files),
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "total_records": total_records,
        }

    return stats
