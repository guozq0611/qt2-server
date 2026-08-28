"""
录制器抽象基类
- 定义所有资产类型录制器的统一接口和公共逻辑
- 子类只需定义各自的 fields_spec（二进制格式）和 asset_type
- 公共逻辑：ZMQ 广播、bin 落盘、Redis 监控、序列号管理
"""
import os
import glob
import time
import queue
import struct
import threading
import re
import json
from datetime import datetime

from core.util.log_util import Logger
from core.util.zmq_util import ZmqPublisher
from core.database.redis.redis_client import RedisClient
from core.entity.base_tick import BaseTick


class BaseRecorder:
    """
    录制器抽象基类

    子类需要：
    1. 定义 self.fields_spec（二进制字段格式列表）
    2. 定义 self.asset_type（资产类型字符串，用于 ZMQ topic 和落盘路径）
    3. 定义 TICK_CLASS（期望的 tick 数据类，用于从共享队列中过滤）
    4. 实现 _extract_pack_values(tick_obj) -> tuple（从 tick 对象提取按 fields_spec 顺序的字段值）
    5. 实现 _extract_redis_snapshot(tick_obj) -> dict（从 tick 对象提取 Redis 快照字典）
    """

    # 子类覆盖：期望的 tick 数据类
    TICK_CLASS = None

    def __init__(self,
                 tick_queue: queue.Queue,
                 asset_type: str,
                 data_dir: str,
                 fields_spec: list,
                 max_records_per_file: int = 500000,
                 zmq_bind_url: str = "tcp://*:5555",
                 zmq_publisher: ZmqPublisher = None):
        self.tick_queue = tick_queue
        self.asset_type = asset_type  # 'future' / 'option' / 'stock'
        self.data_dir = data_dir
        self.max_records_per_file = max_records_per_file
        self.fields_spec = fields_spec

        # 自动编译 struct 格式化字符串 (前缀 '<' 表示小端序)
        fmt_str = '<' + ''.join([spec[1] for spec in self.fields_spec])
        self.tick_struct = struct.Struct(fmt_str)

        # ZMQ 广播（支持共享 Publisher，避免多 Recorder 重复 bind 同一端口）
        self.zmq_publisher = zmq_publisher if zmq_publisher is not None else ZmqPublisher(bind_url=zmq_bind_url)

        # Redis 监控
        self.redis_client = RedisClient().get_client()

        # 落盘目录：current/ 用于实时写入，YYYYMMDD/ 用于历史归档
        self.current_dir = os.path.join(self.data_dir, "current")
        os.makedirs(self.current_dir, exist_ok=True)

        # 运行状态
        self.is_running = False
        self.current_file = None
        self.current_records_count = 0
        self.total_processed_today = 0
        self.last_tick_time = ""
        self.latest_ticks_cache = {}

        # 交易日：先用系统日期占位，第一个 tick 到达后用 tick_obj.trade_date 校正
        # 夜盘 21:00 开始的行情，trade_date 是下一交易日，文件名和归档都归 trade_date
        self.trade_date_str = datetime.now().strftime("%Y%m%d")
        self.current_run_id = 1
        self.current_seq = 1

        # 启动时归档历史文件（把 current/ 里非当天的文件移到 {trade_date}/）
        self._archive_old_files()

        self._init_sequence_number()

        # 启动主线程和监控线程
        self.is_running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)

        self.thread.start()
        self.monitor_thread.start()

    def _archive_old_files(self):
        """启动时把 current/ 里不属于当前 trade_date 的文件归档到 {trade_date}/ 目录"""
        if not os.path.isdir(self.current_dir):
            return

        for fname in os.listdir(self.current_dir):
            if not fname.endswith('.bin'):
                continue
            # 从文件名提取 trade_date: {asset_type}_l1_tick_{YYYYMMDD}_R...
            parts = fname.split('_')
            file_trade_date = None
            for part in parts:
                if len(part) == 8 and part.isdigit():
                    file_trade_date = part
                    break

            if file_trade_date is None:
                continue

            # 如果文件名的 trade_date 跟当前 trade_date 不同，归档
            if file_trade_date != self.trade_date_str:
                archive_dir = os.path.join(self.data_dir, file_trade_date)
                os.makedirs(archive_dir, exist_ok=True)
                src = os.path.join(self.current_dir, fname)
                dst = os.path.join(archive_dir, fname)
                try:
                    os.rename(src, dst)
                    Logger.info(f"[{self.asset_type}] 归档历史文件: {fname} -> {file_trade_date}/")
                except Exception as e:
                    Logger.warning(f"[{self.asset_type}] 归档失败 {fname}: {e}")

    def _init_sequence_number(self):
        pattern = os.path.join(self.current_dir, f"{self.asset_type}_l1_tick_{self.trade_date_str}_R*.bin")
        existing_files = glob.glob(pattern)

        max_run_id = 0
        for f in existing_files:
            try:
                base_name = os.path.basename(f)
                parts = base_name.split('_')
                for part in parts:
                    if part.startswith('R') and part[1:].isdigit():
                        run_id = int(part[1:])
                        max_run_id = max(max_run_id, run_id)
            except Exception:
                continue

        self.current_run_id = max_run_id + 1
        self.current_seq = 1
        Logger.info(f"[{self.asset_type}] 交易日 {self.trade_date_str} 第 {self.current_run_id} 次启动录制引擎，历史批次扫描完毕。")

    def _open_new_file(self):
        if self.current_file:
            self.current_file.close()

        self.current_records_count = 0

        now_time_str = datetime.now().strftime("%H%M%S")
        filename = f"{self.asset_type}_l1_tick_{self.trade_date_str}_R{self.current_run_id}_{now_time_str}_{self.current_seq:03d}.bin"

        self.bin_path = os.path.join(self.current_dir, filename)
        self.current_file = open(self.bin_path, 'ab')

        Logger.info(f"[{self.asset_type}] 开启行情录制切片: {filename}")
        self.current_seq += 1

    def _run(self):
        self._open_new_file()

        while self.is_running:
            try:
                tick_obj: BaseTick = self.tick_queue.get(timeout=1.0)

                # 类型过滤：跳过不属于本录制器的 tick（共享队列场景）
                if self.TICK_CLASS is not None and not isinstance(tick_obj, self.TICK_CLASS):
                    continue

                # 用 tick 的 trade_date 校正交易日（夜盘 21:00 的 trade_date 是下一交易日）
                tick_trade_date = str(tick_obj.trade_date) if tick_obj.trade_date else None
                if tick_trade_date and tick_trade_date != self.trade_date_str:
                    # trade_date 变了（跨日或夜盘开始），归档旧文件并切换
                    self._archive_old_files()
                    self.trade_date_str = tick_trade_date
                    self.current_run_id = 1
                    self.current_seq = 1
                    Logger.info(f"[{self.asset_type}] 交易日切换为 {self.trade_date_str}，重新初始化序列号")
                    self._init_sequence_number()
                    self.current_file.flush()
                    self.current_file.close()
                    self._open_new_file()

                # 子类提供：从 tick 对象提取按 fields_spec 顺序的字段值
                pack_values = self._extract_pack_values(tick_obj)

                # 极速二进制打包
                bin_data = self.tick_struct.pack(*pack_values)

                # ZMQ 广播（topic: TICK.{asset_type}.{product_id}）
                # 提取品种代码：期货 IF2609→IF，期权 IO2603-C-3900→IO
                # 股票期权 510050C2603M02500→510050（标的证券代码）
                if self.asset_type == 'stock_option':
                    m = re.match(r'^(\d{6})', tick_obj.instrument_id)
                    product_id = m.group(1) if m else tick_obj.instrument_id.upper()
                else:
                    m = re.match(r'^[A-Za-z]+', tick_obj.instrument_id)
                    product_id = m.group().upper() if m else tick_obj.instrument_id.upper()
                topic = f"TICK.{self.asset_type.upper()}.{product_id}"
                self.zmq_publisher.publish(topic, bin_data)

                # 异步落盘
                self.current_file.write(bin_data)

                self.current_records_count += 1
                self.total_processed_today += 1
                self.last_tick_time = f"{tick_obj.update_time:06d}.{tick_obj.update_millisec:03d}"

                # 更新最新行情快照
                self.latest_ticks_cache[tick_obj.instrument_id] = tick_obj

                if self.current_records_count >= self.max_records_per_file:
                    self.current_file.flush()
                    self._open_new_file()

            except queue.Empty:
                continue
            except Exception as e:
                Logger.error(f"[{self.asset_type}] 写入 Bin 文件发生异常: {e}")

    def stop(self):
        self.is_running = False
        if self.thread.is_alive():
            self.thread.join()
        if self.current_file:
            self.current_file.flush()
            self.current_file.close()
        Logger.info(f"[{self.asset_type}] Recorder 已安全关闭，数据已完全刷入磁盘。")

    def _monitor_loop(self):
        """旁路监控线程：每 2 秒向 Redis 推送一次系统快照"""
        sys_key = f"qt2:monitor:{self.asset_type}_sys_health"
        state_key = f"qt2:state:{self.asset_type}_latest_tick"

        while self.is_running:
            if not self.redis_client:
                time.sleep(5)
                continue

            try:
                # 系统健康指标
                q_size = self.tick_queue.qsize()
                metrics = {
                    "status": "running",
                    "heartbeat": int(time.time()),
                    "queue_size": q_size,
                    "total_processed": self.total_processed_today,
                    "last_update": self.last_tick_time
                }
                self.redis_client.hset(sys_key, mapping=metrics)
                self.redis_client.expire(sys_key, 10)

                # 全市场行情快照
                if self.latest_ticks_cache:
                    snapshot = self.latest_ticks_cache.copy()
                    redis_mapping = {}
                    M = 10000.0

                    for symbol, t in snapshot.items():
                        # 子类提供：从 tick 对象提取 Redis 快照字典
                        tick_dict = self._extract_redis_snapshot(t, M)
                        redis_mapping[symbol] = json.dumps(tick_dict)

                    if redis_mapping:
                        self.redis_client.hset(state_key, mapping=redis_mapping)

            except Exception:
                pass

            time.sleep(2.0)

    # ==========================================================
    # 子类必须实现的抽象方法
    # ==========================================================

    def _extract_pack_values(self, tick_obj) -> tuple:
        """从 tick 对象提取按 fields_spec 顺序的字段值，用于 struct.pack"""
        raise NotImplementedError

    def _extract_redis_snapshot(self, tick_obj, multiplier: float) -> dict:
        """从 tick 对象提取 Redis 快照字典"""
        raise NotImplementedError
