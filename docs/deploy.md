# qt2-server 部署工作流

> 三环境 git 管理：本机开发 → home01 测试 → home01 生产（tag 发布）

## 环境拓扑

| 环境 | 位置 | Git 策略 | 用途 |
|------|------|----------|------|
| **开发** | 本机 `~/work/Projects/qt2-server` | main 分支，直接 commit | 日常开发、调试 |
| **测试** | home01 `~/work/Projects/qt2-server` | `git pull origin main` | 集成测试、联调 |
| **生产** | home01 `~/prod/qt2-server` | `git checkout v1.0.0`（tag） | 稳定运行 |

```
GitHub (guozq0611/qt2-server)
  │
  ├── main ──────────────► 测试环境 git pull
  │   (持续集成)
  │
  └── v1.0.0 tag ─────────► 生产环境 git checkout
      (稳定发布)
```

## 前置条件

- GitHub 仓库：`git@github.com:guozq0611/qt2-server.git`
- home01 SSH：`ssh guozq0611@home01`（证书认证）
- home01 Python：3.12 + venv
- home01 Node：v20 + npm
- home01 systemd user service：`qt2-api.service`
- home01 本地 MySQL（127.0.0.1:21707）+ Redis（127.0.0.1:21708）

## 日常开发流程

### 1. 本机开发

```bash
cd ~/work/Projects/qt2-server

# 改代码...
# 本地测试...
source .venv/bin/activate
python run/run_api.py --port 8000  # 本地启动 API
cd frontend && npm run dev          # 本地启动前端

# 提交
git add .
git commit -m "feat: xxx"
git push origin main
```

### 2. 测试环境同步

```bash
ssh guozq0611@home01
cd ~/work/Projects/qt2-server
git pull origin main

# 如有新依赖
source .venv/bin/activate
pip install -r requirements.txt

# 如有前端改动
cd frontend && npm install && npm run build

# 启动测试（端口 8011，避免和生产 8010 冲突）
python run/run_api.py --host 0.0.0.0 --port 8011
```

### 3. 生产发布

#### 方式 A：一键部署脚本（推荐）

```bash
cd ~/work/Projects/qt2-server

# 更新 VERSION 文件
echo "1.0.1" > VERSION

# 部署（自动 commit VERSION + tag + push + 远程部署）
./scripts/deploy.sh
```

#### 方式 B：手动部署

```bash
# 1. 更新版本号
echo "1.0.1" > VERSION
git add VERSION
git commit -m "release: bump version to 1.0.1"
git push origin main

# 2. 打 tag
git tag v1.0.1
git push origin v1.0.1

# 3. 远程部署
ssh guozq0611@home01
cd ~/prod/qt2-server
cp .env /tmp/qt2_deploy.env.bak
git fetch --tags
git checkout v1.0.1
cp /tmp/qt2_deploy.env.bak .env

# 4. 更新依赖 + 重建前端
source .venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..

# 5. 重启服务
systemctl --user restart qt2-api

# 6. 冒烟测试
curl http://127.0.0.1:8010/health
curl http://127.0.0.1:8010/api/instruments/summary
```

## 回滚

```bash
# 一键回滚
./scripts/deploy.sh --rollback v1.0.0

# 或手动
ssh guozq0611@home01
cd ~/prod/qt2-server
git fetch --tags
git checkout v1.0.0  # 回到上一个稳定版本
systemctl --user restart qt2-api
```

## 版本号规范

遵循 SemVer：`v{major}.{minor}.{patch}`

| 变更类型 | 示例 |
|----------|------|
| 修 bug | v1.0.0 → v1.0.1 |
| 加功能（向后兼容） | v1.0.1 → v1.1.0 |
| 破坏性变更 | v1.1.0 → v2.0.0 |

## Tag vs Branch

| | Tag（采用） | Branch |
|---|---|---|
| 语义 | 标记发布版本，不可变 | 持续演进，可变 |
| 回滚 | `git checkout v1.0.0` 直接回滚 | 需找历史 commit |
| 审计 | `git tag -l` 列出所有生产版本 | 分支历史混杂 |

**结论：用 Tag。** 每次发布打一个 `v{version}` tag，生产环境 checkout tag 部署。

## 访问方式

| 环境 | 访问方式 |
|------|----------|
| 生产 | `ssh -L 18010:127.0.0.1:8010 guozq0611@home01` → `http://127.0.0.1:18010` |
| 测试 | `ssh -L 18011:127.0.0.1:8011 guozq0611@home01` → `http://127.0.0.1:18011` |

## 进程管理

```bash
# 查看状态
systemctl --user status qt2-api

# 重启
systemctl --user restart qt2-api

# 停止
systemctl --user stop qt2-api

# 查看日志
tail -f ~/prod/qt2-server/logs/api.log
```

## 注意事项

- **生产环境不要手动改代码**，所有修复必须通过 commit → tag → checkout 部署
- **.env 不入 git**，生产环境的 .env 需要在部署后手动确认/恢复
- **前端必须 build**，生产环境用 `frontend/dist` 静态文件，不是 dev server
- **VERSION 文件必须与 tag 一致**，deploy.sh 会自动处理
- 部署前确认本地测试通过
- 未来生产环境可能迁移到其他服务器，只需修改 `scripts/deploy.sh` 中的 `PROD_HOST` 和 `PROD_PATH`
