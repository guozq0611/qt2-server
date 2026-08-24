#!/usr/bin/env bash
#
# qt2-server 生产部署脚本
#
# 用法:
#   ./scripts/deploy.sh              # 读取 VERSION 文件，打 tag 并部署
#   ./scripts/deploy.sh v1.0.1       # 指定版本号部署
#   ./scripts/deploy.sh --rollback v1.0.0  # 回滚到指定版本
#
# 流程:
#   1. 读取 VERSION 文件确定版本号
#   2. git tag + push tag 到 GitHub
#   3. SSH 到 home01 生产环境，git fetch + checkout tag
#   4. 重建 venv 依赖（如有变更）
#   5. 重建前端
#   6. 重启 systemd 服务
#   7. 冒烟测试
#
set -euo pipefail

# ===== 配置 =====
PROD_HOST="guozq0611@home01"
PROD_PATH="~/prod/qt2-server"
SERVICE_NAME="qt2-api"
API_PORT=18010

# ===== 参数解析 =====
ACTION="deploy"
VERSION_ARG=""

case "${1:-}" in
    --rollback)
        ACTION="rollback"
        VERSION_ARG="${2:?用法: deploy.sh --rollback <version>}"
        ;;
    -h|--help)
        echo "用法:"
        echo "  deploy.sh              读取 VERSION 文件，打 tag 并部署"
        echo "  deploy.sh v1.0.1       指定版本号部署"
        echo "  deploy.sh --rollback v1.0.0   回滚到指定版本"
        exit 0
        ;;
    "")
        # 从 VERSION 文件读取
        VERSION_ARG=$(cat VERSION 2>/dev/null || echo "")
        if [ -z "$VERSION_ARG" ]; then
            echo "错误: VERSION 文件不存在或为空"
            exit 1
        fi
        ;;
    *)
        VERSION_ARG="$1"
        ;;
esac

# 确保版本号有 v 前缀
TAG="v${VERSION_ARG#v}"
echo "============================================"
echo "  qt2-server 部署"
echo "  动作: $ACTION"
echo "  版本: $TAG"
echo "  目标: $PROD_HOST:$PROD_PATH"
echo "============================================"

# ===== 部署流程 =====
if [ "$ACTION" = "deploy" ]; then
    # 1. 检查工作区干净
    if [ -n "$(git status --porcelain)" ]; then
        echo "⚠️  本地有未提交的改动:"
        git status --short
        echo ""
        echo "请先 commit 再部署。"
        exit 1
    fi

    # 2. 检查 tag 是否已存在
    if git rev-parse "$TAG" >/dev/null 2>&1; then
        echo "⚠️  Tag $TAG 已存在。如需重新部署，先删除: git tag -d $TAG"
        exit 1
    fi

    # 3. 更新 VERSION 文件（如果版本号不一致）
    CURRENT_VERSION=$(cat VERSION 2>/dev/null || echo "")
    if [ "$CURRENT_VERSION" != "${VERSION_ARG}" ]; then
        echo "$VERSION_ARG" > VERSION
        git add VERSION
        git commit -m "release: bump version to $VERSION_ARG"
        echo "✓ VERSION 文件已更新并提交"
    fi

    # 4. 推送 main + 打 tag
    echo "--- 推送 main 分支 ---"
    git push origin main
    echo "--- 打 tag $TAG ---"
    git tag "$TAG"
    git push origin "$TAG"
    echo "✓ Tag $TAG 已推送到 GitHub"

elif [ "$ACTION" = "rollback" ]; then
    echo "--- 回滚到 $TAG ---"
    # 检查 tag 是否存在
    if ! git rev-parse "$TAG" >/dev/null 2>&1; then
        echo "⚠️  Tag $TAG 不存在。可用 tags:"
        git tag -l
        exit 1
    fi
fi

# 5. SSH 到生产环境部署
echo ""
echo "--- 远程部署 ---"
ssh "$PROD_HOST" bash -s "$TAG" "$ACTION" << 'REMOTE_SCRIPT'
set -euo pipefail
TAG="$1"
ACTION="$2"
PROD_PATH="$HOME/prod/qt2-server"

echo "远程: $PROD_PATH"
cd "$PROD_PATH"

# 保存 .env（git clone 的没有 .env）
cp .env /tmp/qt2_deploy.env.bak 2>/dev/null || true

echo "--- git fetch --tags ---"
git fetch --tags
git fetch origin

echo "--- git checkout $TAG ---"
git checkout "$TAG"
echo "✓ 已切换到 $TAG"

# 恢复 .env（如果被 checkout 覆盖）
cp /tmp/qt2_deploy.env.bak .env 2>/dev/null || true

echo "--- 更新 Python 依赖 ---"
source .venv/bin/activate
pip install -r requirements.txt -q 2>&1 | tail -3 || true

echo "--- 重建前端 ---"
cd frontend
npm install -q 2>&1 | tail -2
npm run build 2>&1 | tail -3
cd ..

echo "--- 重启服务 ---"
systemctl --user restart qt2-api
sleep 3

echo "--- 服务状态 ---"
systemctl --user status qt2-api 2>&1 | head -6

echo "--- 冒烟测试 ---"
HEALTH=$(curl -s http://127.0.0.1:18010/health || echo "FAIL")
if [ "$HEALTH" = '{"status":"ok"}' ]; then
    echo "✓ health check passed"
else
    echo "✗ health check FAILED: $HEALTH"
    exit 1
fi

INSTRUMENTS=$(curl -s http://127.0.0.1:18010/api/instruments/summary | python3 -c "import sys,json; print(json.load(sys.stdin).get('total','?'))" 2>/dev/null || echo "FAIL")
if [ "$INSTRUMENTS" != "FAIL" ]; then
    echo "✓ instruments check passed (total=$INSTRUMENTS)"
else
    echo "✗ instruments check FAILED"
    exit 1
fi

echo ""
echo "============================================"
echo "  部署完成: $TAG"
echo "  访问: ssh -L 18010:127.0.0.1:18010 $USER@home01"
echo "  浏览器: http://127.0.0.1:18010"
echo "============================================"
REMOTE_SCRIPT

echo ""
echo "✓ 全部完成"
