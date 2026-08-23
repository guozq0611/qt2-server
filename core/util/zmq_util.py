"""
ZeroMQ 发布/订阅工具
- ZmqPublisher: 行情广播（主进程用）
- ZmqSubscriber: 行情订阅（下游消费方用）
"""
import zmq
from core.util.log_util import Logger


class ZmqPublisher:
    """
    ZMQ 发布者
    特性：非阻塞、高水位线保护、零拷贝发送
    """
    def __init__(self, bind_url: str = "tcp://127.0.0.1:5555", hwm: int = 2000):
        self.bind_url = bind_url
        self.hwm = hwm

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)

        # 设置发送高水位线 (High Water Mark)
        # 如果下游卡死了，ZMQ 内存队列最多只积压 hwm 条数据，超过的直接丢弃老数据
        self.socket.setsockopt(zmq.SNDHWM, self.hwm)

        try:
            self.socket.bind(self.bind_url)
            Logger.info(f"ZMQ Publisher successfully bound at {self.bind_url} (HWM: {self.hwm})")
        except Exception as e:
            Logger.error(f"ZMQ Publisher failed to bind at {self.bind_url}: {e}")
            raise e

    def publish(self, topic: str, raw_bytes: bytes):
        """
        极速广播：底层自动扔进独立的 C++ I/O 线程，耗时纳秒级，绝对不阻塞主线程
        """
        try:
            # 发送多段消息：[主题, 二进制载荷]
            self.socket.send_multipart([topic.encode('utf-8'), raw_bytes])
        except Exception as e:
            # 即便 ZMQ 内部出错，也绝不能抛出异常导致主程序崩溃
            Logger.error(f"ZMQ Publish Error on topic {topic}: {e}")

    def close(self):
        """优雅退出"""
        self.socket.close()
        self.context.term()


class ZmqSubscriber:
    """
    ZMQ 订阅者 (价差计算、落盘等程序使用)
    """
    def __init__(self, connect_url: str = "tcp://127.0.0.1:5555"):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)

        try:
            self.socket.connect(connect_url)
            Logger.info(f"ZMQ Subscriber successfully connected to {connect_url}")
        except Exception as e:
            Logger.error(f"ZMQ Subscriber failed to connect to {connect_url}: {e}")
            raise e

    def subscribe(self, topic: str):
        """订阅特定主题 (如 'TICK.FUTURE.IF' 会收到所有 IF 合约的数据)"""
        self.socket.setsockopt(zmq.SUBSCRIBE, topic.encode('utf-8'))
        Logger.info(f"Subscribed to topic: {topic}")

    def receive(self):
        """阻塞等待接收数据 (底层是 epoll，极度节省 CPU)"""
        topic_bytes, raw_bytes = self.socket.recv_multipart()
        return topic_bytes.decode('utf-8'), raw_bytes

    def close(self):
        """优雅退出"""
        self.socket.close()
        self.context.term()
