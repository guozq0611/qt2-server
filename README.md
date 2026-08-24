# qt2-server

Multi-asset market data gateway: CTP futures/options, stock L2.

## 功能

- **CTP 行情接收**：通过 CTP 接口接收国内期货交易所全市场行情（中金所/上期/大商/郑商/能源/广期）
- **期权行情**：CTP 同一连接可同时接收期权行情（股指期权/商品期权）
- **ZeroMQ 分发**：所有 tick 通过 ZMQ PUB/SUB 极速广播，下游可按 topic 订阅
- **二进制落盘**：bin 格式极速落盘，对齐 ClickHouse Int64，下游可零拷贝消费
- **Redis 监控**：系统健康指标 + 全市场最新行情快照，每 2 秒上报一次
- **多网关架构**：BaseMdGateway 抽象基类，支持扩展股票 L2 等数据源

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

```bash
cp .env.example .env
# 编辑 .env 填写真实配置（MySQL/Redis/CTP 等）
```

### 3. 启动

```bash
cd /path/to/qt2-server

# 默认按 .env 配置启动
python run/run_market_data.py

# 命令行覆盖：只跑 CTP 期货
python run/run_market_data.py --gateway ctp --assets future

# CTP 期货+期权
python run/run_market_data.py --gateway ctp --assets future,option

# 只跑 CTP 期权
python run/run_market_data.py --gateway ctp --assets option

# 查看帮助
python run/run_market_data.py --help
```

**参数说明**：
- `--gateway`：启用的网关，逗号分隔（覆盖 .env 的 `GATEWAYS`）
- `--assets`：订阅的资产类型，逗号分隔（覆盖 .env 的 `CTP_SUBSCRIBE_ASSET_TYPES`）
- 不传参数时走 `.env` 默认配置
- 单例锁按服务组合区分，不同 `--gateway`/`--assets` 组合可并行运行

## 架构

```
┌─────────────────────────────────────────────────────────┐
│                    run_market_data.py                    │
│                   (主入口 + 监控循环)                     │
└──────────┬──────────────────────────┬────────────────────┘
           │                          │
           ▼                          ▼
┌─────────────────────┐    ┌─────────────────────┐
│   Gateway 层        │    │   Recorder 层       │
│  (连接数据源)        │    │  (落盘+广播+监控)    │
│                     │    │                     │
│  BaseMdGateway      │    │  BaseRecorder       │
│   ├─ CtpMdGateway   │    │   ├─ FutureRecorder │
│   └─ StockL2Gateway │    │   ├─ OptionRecorder │
│                      │    │   └─ StockL2Recorder│
└─────────┬───────────┘    └─────────┬───────────┘
          │                          │
          │   tick_queue (内存队列)   │
          └──────────────────────────┘
                     │
                     ▼
          ┌──────────────────┐
          │  ZMQ PUB (广播)  │
          │  Bin 文件 (落盘) │
          │  Redis (监控)    │
          └──────────────────┘
```

## ZMQ Topic 规范

```
TICK.{ASSET_TYPE}.{PRODUCT_ID}
```

| Topic | 含义 |
|---|---|
| `TICK.FUTURE.IF` | 期货 - 中金所股指 |
| `TICK.FUTURE.CU` | 期货 - 上期所铜 |
| `TICK.OPTION.IO` | 期权 - 中金所股指期权 |
| `TICK.STOCK.000001` | 股票 - 平安银行 |

## Bin 落盘格式

### 期货（160 字节/条，小端序）

| 字段 | 类型 | 字节 |
|---|---|---|
| instrument_id | 16s | 16 |
| exchange_id | 8s | 8 |
| trade_date | i | 4 |
| action_date | i | 4 |
| update_time | i | 4 |
| update_millisec | i | 4 |
| local_time_ns | q | 8 |
| last_price | q | 8 |
| volume | q | 8 |
| turnover | q | 8 |
| open_interest | q | 8 |
| bid_price_1 | q | 8 |
| bid_volume_1 | q | 8 |
| ask_price_1 | q | 8 |
| ask_volume_1 | q | 8 |
| open_price | q | 8 |
| highest_price | q | 8 |
| lowest_price | q | 8 |
| average_price | q | 8 |
| upper_limit_price | q | 8 |
| lower_limit_price | q | 8 |

价格字段已放大 10000 倍存为 Int64，turnover 放大 100 倍。

### 期权

在期货 160 字节基础上扩展期权专属字段（underlying/strike/type/expiry/Greeks，共 70 字节），合计 230 字节/条，详见 `data_process/option_tick_recorder.py`。

## 目录结构

```
qt2-server/
├── core/                       # 基础通用层（供业务模块调用）
│   ├── common/                 # 常量、枚举
│   ├── setting/                # 配置入口
│   ├── util/                   # 工具类（log/db/process/zmq）
│   ├── database/redis/         # Redis 客户端
│   ├── entity/                 # Tick 数据结构（base/future/option/stock）
│   ├── gateway/base_gateway.py # 网关抽象基类
│   └── data_process/base_recorder.py  # 录制器抽象基类
├── gateway/                    # 业务层 - 行情网关（ctp/stock_l2）
├── data_process/               # 业务层 - 录制器（future/option/stock）
├── repository/                 # 业务层 - 数据仓库（trade_calendar/instrument/）
├── run/                        # 启动入口
├── config/                     # 配置模板
├── data/                       # 运行时落盘目录
├── logs/                       # 运行时日志目录
└── requirements.txt
```

## 扩展新数据源

1. 在 `core/entity/` 新增 tick 数据结构（继承 BaseTick）
2. 在 `gateway/` 新增网关（继承 core.gateway.base_gateway.BaseMdGateway）
3. 在 `data_process/` 新增录制器（继承 core.data_process.base_recorder.BaseRecorder）
4. 在 `repository/instrument/` 新增合约信息仓库
5. 在 `run/run_market_data.py` 的 `GATEWAY_REGISTRY` 注册网关
6. 在 `setting.local.json` 的 `gateways` 列表启用
