"""
落盘文件路由

列出 data/raw 下的 bin 文件，按资产类型和日期分组
"""
import os
import glob
from datetime import datetime
from fastapi import APIRouter, Query

from core.setting.setting import DATA_DIR


router = APIRouter()


@router.get("/list")
async def list_files(
    asset_type: str = Query("future", description="资产类型: future / option"),
    date: str = Query(None, description="日期过滤 YYYYMMDD"),
):
    """列出落盘的 bin 文件"""
    base_dir = os.path.join(DATA_DIR, asset_type, "level1", "tick")
    if not os.path.isdir(base_dir):
        return {"asset_type": asset_type, "count": 0, "files": []}

    pattern = "*.bin"
    if date:
        pattern = f"*{date}*.bin"

    files = glob.glob(os.path.join(base_dir, pattern))
    files.sort(key=lambda f: os.path.getmtime(f), reverse=True)

    result = []
    for fpath in files:
        fname = os.path.basename(fpath)
        fsize = os.path.getsize(fpath)
        mtime = datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%Y-%m-%d %H:%M:%S")
        # bin 文件每条记录 160 字节（future）或 230 字节（option）
        record_size = 160 if asset_type == "future" else 230
        record_count = fsize // record_size if fsize > 0 else 0

        result.append({
            "filename": fname,
            "size_bytes": fsize,
            "size_mb": round(fsize / 1024 / 1024, 2),
            "record_count": record_count,
            "modified": mtime,
        })

    return {"asset_type": asset_type, "count": len(result), "files": result}


@router.get("/stats")
async def files_stats():
    """落盘文件统计"""
    stats = {}

    for asset_type in ["future", "option"]:
        base_dir = os.path.join(DATA_DIR, asset_type, "level1", "tick")
        if not os.path.isdir(base_dir):
            stats[asset_type] = {"file_count": 0, "total_size_mb": 0, "total_records": 0}
            continue

        files = glob.glob(os.path.join(base_dir, "*.bin"))
        record_size = 160 if asset_type == "future" else 230
        total_size = sum(os.path.getsize(f) for f in files)
        total_records = total_size // record_size

        stats[asset_type] = {
            "file_count": len(files),
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "total_records": total_records,
        }

    return stats
