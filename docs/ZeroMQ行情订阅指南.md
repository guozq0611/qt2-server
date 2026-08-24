# ZeroMQ 股指期货行情订阅指南

> **适用对象**：需要从 qt2-server 实时获取股指期货行情的下游开发者
> **协议**：ZeroMQ PUB/SUB
> **数据格式**：二进制 struct（小端序，160 字节/条）

---

## 1. 连接信息

| 项目 | 值 |
|------|------|
| 协议 | ZeroMQ PUB/SUB |
| 服务器地址 | `tcp://<server_ip>:5556` |
| Socket 类型 | SUB（订阅端） |
| 编码 | Little-Endian（小端序） |

> **生产环境地址**：请向管理员确认实际 IP 和端口。
> 当前生产环境为 `tcp://127.0.0.1:5556`。

---

## 2. 主题（Topic）命名规则

```
TICK.{资产类型}.{品种代码}
```

### 股指期货品种

| 品种代码 | 全称 | 交易所 | 主题 |
|----------|------|--------|------|
| IF | 沪深300股指期货 | CFFEX | `TICK.FUTURE.IF` |
| IH | 上证50股指期货 | CFFEX | `TICK.FUTURE.IH` |
| IC | 中证500股指期货 | CFFEX | `TICK.FUTURE.IC` |
| IM | 中证1000股指期货 | CFFEX | `TICK.FUTURE.IM` |

### 订阅方式

- **订阅某个品种**（如只订阅 IF）：`TICK.FUTURE.IF`
- **订阅全部股指期货**：`TICK.FUTURE.I`（前缀匹配，会收到 IF/IH/IC/IM）
- **订阅全部期货**：`TICK.FUTURE.`（前缀匹配）

> ZMQ SUB 的订阅是**前缀匹配**，订阅 `TICK.FUTURE.I` 会收到所有以该字符串开头的主题消息。

---

## 3. 消息格式

每条消息是一个 **multipart frame**，包含 2 个 frame：

| Frame | 内容 | 说明 |
|-------|------|------|
| Frame 0 | Topic（UTF-8 字符串） | 如 `TICK.FUTURE.IF` |
| Frame 1 | 二进制数据（160 字节） | struct 打包的 tick 数据 |

---

## 4. 二进制数据结构（160 字节）

数据使用 C struct 格式，**小端序**，共 21 个字段：

| 序号 | 字段名 | 类型 | 大小(字节) | C# 类型 | 说明 |
|------|--------|------|-----------|---------|------|
| 1 | instrument_id | char[16] | 16 | `string`（截断） | 合约代码，如 `IF2609` |
| 2 | exchange_id | char[8] | 8 | `string`（截断） | 交易所，如 `CFFEX` |
| 3 | trade_date | int32 | 4 | `int` | 交易日，如 `20260824` |
| 4 | action_date | int32 | 4 | `int` | 实际交易日 |
| 5 | update_time | int32 | 4 | `int` | 时间 HHMMSS，如 `145700` |
| 6 | update_millisec | int32 | 4 | `int` | 毫秒，0-999 |
| 7 | local_time_ns | int64 | 8 | `long` | 本地接收纳秒时间戳 |
| 8 | last_price | int64 | 8 | `long` | 最新价（**×10000**） |
| 9 | volume | int64 | 8 | `long` | 累计成交量 |
| 10 | turnover | int64 | 8 | `long` | 累计成交金额（**×10000**） |
| 11 | open_interest | int64 | 8 | `long` | 持仓量 |
| 12 | bid_price_1 | int64 | 8 | `long` | 买一价（**×10000**） |
| 13 | bid_volume_1 | int64 | 8 | `long` | 买一量 |
| 14 | ask_price_1 | int64 | 8 | `long` | 卖一价（**×10000**） |
| 15 | ask_volume_1 | int64 | 8 | `long` | 卖一量 |
| 16 | open_price | int64 | 8 | `long` | 开盘价（**×10000**） |
| 17 | highest_price | int64 | 8 | `long` | 最高价（**×10000**） |
| 18 | lowest_price | int64 | 8 | `long` | 最低价（**×10000**） |
| 19 | average_price | int64 | 8 | `long` | 均价（**×10000**） |
| 20 | upper_limit_price | int64 | 8 | `long` | 涨停价（**×10000**） |
| 21 | lower_limit_price | int64 | 8 | `long` | 跌停价（**×10000**） |
| | | **合计** | **160** | | |

### ⚠️ 价格字段说明

所有价格字段（last_price、bid_price_1、ask_price_1、open_price 等）均为 **int64 整数，已放大 10000 倍**。

**还原真实价格**：`真实价格 = 字段值 / 10000.0`

例如：
- `last_price = 38562000` → 真实价格 = `3856.2`
- `bid_price_1 = 38560000` → 买一价 = `3856.0`

### 字符串字段说明

`instrument_id` 和 `exchange_id` 是固定长度的 char 数组，末尾可能包含 `\0` 填充。
解析时需要截断到第一个 `\0` 的位置。

---

## 5. C# 完整示例代码

### 5.1 安装依赖

使用 [NetMQ](https://github.com/zeromq/netmq) 库：

```bash
dotnet add package NetMQ
```

### 5.2 数据结构定义

```csharp
using System;
using System.Runtime.InteropServices;

public struct FutureTick
{
    [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 16)]
    public string InstrumentId;      // 合约代码

    [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 8)]
    public string ExchangeId;        // 交易所

    public int TradeDate;            // 交易日 20260824
    public int ActionDate;           // 实际交易日
    public int UpdateTime;           // HHMMSS
    public int UpdateMillisec;       // 毫秒 0-999
    public long LocalTimeNs;         // 本地纳秒时间戳
    public long LastPrice;           // 最新价 ×10000
    public long Volume;              // 累计成交量
    public long Turnover;            // 累计成交金额 ×10000
    public long OpenInterest;        // 持仓量
    public long BidPrice1;           // 买一价 ×10000
    public long BidVolume1;          // 买一量
    public long AskPrice1;           // 卖一价 ×10000
    public long AskVolume1;          // 卖一量
    public long OpenPrice;           // 开盘价 ×10000
    public long HighestPrice;        // 最高价 ×10000
    public long LowestPrice;         // 最低价 ×10000
    public long AveragePrice;        // 均价 ×10000
    public long UpperLimitPrice;     // 涨停价 ×10000
    public long LowerLimitPrice;     // 跌停价 ×10000

    // 真实价格（除以 10000）
    public double LastPriceReal => LastPrice / 10000.0;
    public double BidPrice1Real => BidPrice1 / 10000.0;
    public double AskPrice1Real => AskPrice1 / 10000.0;
    public double OpenPriceReal => OpenPrice / 10000.0;
    public double HighestPriceReal => HighestPrice / 10000.0;
    public double LowestPriceReal => LowestPrice / 10000.0;
    public double TurnoverReal => Turnover / 10000.0;

    // 格式化时间
    public string UpdateTimeStr
    {
        get
        {
            int h = UpdateTime / 10000;
            int m = (UpdateTime % 10000) / 100;
            int s = UpdateTime % 100;
            return $"{h:D2}:{m:D2}:{s:D2}.{UpdateMillisec:D3}";
        }
    }
}
```

### 5.3 订阅程序

```csharp
using System;
using NetMQ;
using NetMQ.Sockets;
using System.Text;
using System.Runtime.InteropServices;

class Program
{
    static void Main(string[] args)
    {
        // ZMQ 上下文
        using (var subSocket = new SubscriberSocket())
        {
            // 连接服务器
            string serverUrl = "tcp://127.0.0.1:5556";
            subSocket.Connect(serverUrl);
            Console.WriteLine($"已连接到 {serverUrl}");

            // 订阅股指期货主题（IF / IH / IC / IM）
            // 方式1：逐个订阅
            subSocket.Subscribe("TICK.FUTURE.IF");
            subSocket.Subscribe("TICK.FUTURE.IH");
            subSocket.Subscribe("TICK.FUTURE.IC");
            subSocket.Subscribe("TICK.FUTURE.IM");

            // 方式2：前缀订阅（订阅所有以 TICK.FUTURE.I 开头的主题）
            // subSocket.Subscribe("TICK.FUTURE.I");

            // 方式3：订阅全部期货
            // subSocket.Subscribe("TICK.FUTURE.");

            Console.WriteLine("开始接收行情... 按 Ctrl+C 退出\n");

            while (true)
            {
                // 接收 multipart message
                var topicBytes = subSocket.ReceiveFrameBytes();
                var dataBytes = subSocket.ReceiveFrameBytes();

                string topic = Encoding.UTF8.GetString(topicBytes);

                // 解析二进制数据（160 字节）
                if (dataBytes.Length >= 160)
                {
                    var tick = BytesToStruct<FutureTick>(dataBytes);

                    // 截断字符串中的 \0
                    string symbol = tick.InstrumentId.Split('\0')[0];
                    string exchange = tick.ExchangeId.Split('\0')[0];

                    Console.WriteLine(
                        $"[{topic}] {symbol}.{exchange} " +
                        $"时间={tick.UpdateTimeStr} " +
                        $"最新价={tick.LastPriceReal:F2} " +
                        $"量={tick.Volume} " +
                        $"持仓={tick.OpenInterest} " +
                        $"买一={tick.BidPrice1Real:F2}×{tick.BidVolume1} " +
                        $"卖一={tick.AskPrice1Real:F2}×{tick.AskVolume1}"
                    );
                }
            }
        }
    }

    /// <summary>
    /// byte[] 转 struct（小端序）
    /// </summary>
    static T BytesToStruct<T>(byte[] bytes) where T : struct
    {
        GCHandle handle = GCHandle.Alloc(bytes, GCHandleType.Pinned);
        try
        {
            // 确保小端序
            if (!BitConverter.IsLittleEndian)
            {
                // 大端系统需要手动翻转，PC 上一般不需要
                throw new NotSupportedException("请使用小端序系统");
            }
            int size = Marshal.SizeOf(typeof(T));
            IntPtr ptr = handle.AddrOfPinnedObject();
            return (T)Marshal.PtrToStructure(ptr, typeof(T));
        }
        finally
        {
            handle.Free();
        }
    }
}
```

### 5.4 输出示例

```
[TICK.FUTURE.IF] IF2609.CFFEX 时间=14:35:22.125 最新价=3856.20 量=12450 持仓=89000 买一=3856.00×3 卖一=3856.40×2
[TICK.FUTURE.IH] IH2609.CFFEX 时间=14:35:22.130 最新价=2648.80 量=5600 持仓=42000 买一=2648.60×5 卖一=2649.00×1
[TICK.FUTURE.IC] IC2609.CFFEX 时间=14:35:22.135 最新价=5920.40 量=8200 持仓=67000 买一=5920.20×2 卖一=5920.60×4
[TICK.FUTURE.IM] IM2609.CFFEX 时间=14:35:22.140 最新价=6450.00 量=3100 持仓=28000 买一=6449.80×1 卖一=6450.20×3
```

---

## 6. 交易时段

股指期货仅在以下时段有行情推送：

| 时段 | 时间 |
|------|------|
| 日盘上午 | 09:30 - 11:30 |
| 日盘下午 | 13:00 - 15:00 |
| 夜盘（无） | 股指期货无夜盘 |

> 非交易时段连接不会有数据推送，但连接会保持。

---

## 7. 注意事项

1. **价格放大 10000 倍**：所有价格字段是 int64 整数，使用时必须 `/ 10000.0` 还原。
2. **字符串截断**：`instrument_id`（16字节）和 `exchange_id`（8字节）是定长 char 数组，末尾有 `\0` 填充，解析时需截断。
3. **小端序**：数据使用 Little-Endian 编码，Windows x86/x64 默认是小端序，无需额外处理。
4. **订阅是前缀匹配**：`Subscribe("TICK.FUTURE.I")` 会收到 IF、IH、IC、IM 所有消息。
5. **消息速率**：交易时段每个品种约 2-5 条/秒，4 个股指品种合计约 10-20 条/秒。
6. **无心跳机制**：ZMQ PUB/SUB 协议本身不提供心跳，如需检测连接状态请自行实现。
7. **启动顺序**：PUB 端先启动，SUB 后连接。如果 SUB 先连接，在 PUB 启动前的消息会丢失（ZMQ 的 slow joiner 问题）。

---

## 8. Python 参考代码（用于验证）

如果需要快速验证数据格式是否正确，可以用 Python：

```python
import zmq
import struct

# 连接
context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://127.0.0.1:5556")
socket.subscribe(b"TICK.FUTURE.IF")

# struct 格式（小端序）
FMT = '<16s8siiiiqqqqqqqqqqqqqqqq'
SIZE = struct.calcsize(FMT)  # 160

while True:
    topic, data = socket.recv_multipart()
    fields = struct.unpack(FMT, data)

    symbol = fields[0].split(b'\0')[0].decode()
    exchange = fields[1].split(b'\0')[0].decode()
    trade_date = fields[2]
    update_time = fields[4]
    update_ms = fields[5]
    last_price = fields[7] / 10000.0
    volume = fields[8]

    print(f"[{topic.decode()}] {symbol}.{exchange} "
          f"{trade_date} {update_time:06d}.{update_ms:03d} "
          f"price={last_price:.2f} vol={volume}")
```

---

## 9. 故障排查

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 收不到消息 | 1) 服务器未启动 2) 端口不通 3) 主题不匹配 | 检查行情引擎进程、防火墙、订阅主题拼写 |
| 收到消息但解析乱码 | 字节序不对 / struct 格式不匹配 | 确认使用小端序，确认 160 字节格式 |
| 价格异常大 | 没有除以 10000 | 所有价格字段 `/ 10000.0` |
| 合约名乱码 | 没有截断 `\0` | `str.Split('\0')[0]` |
| 连接后等很久才有数据 | ZMQ slow joiner | 启动后等待几秒，PUB 端需要发现 SUB |

---

## 10. 联系方式

如有问题，请联系管理员确认：
- 服务器 IP 和端口
- 行情引擎是否在运行
- 网络是否可达
