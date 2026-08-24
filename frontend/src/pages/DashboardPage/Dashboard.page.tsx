import React, { useEffect, useState } from 'react';
import PageWrapper from '../../components/layouts/PageWrapper/PageWrapper';
import Container from '../../components/layouts/Container/Container';
import Subheader, { SubheaderLeft, SubheaderRight } from '../../components/layouts/Subheader/Subheader';
import Card, { CardBody } from '../../components/ui/Card';
import Badge from '../../components/ui/Badge';
import api from '../../api';

interface RecorderStatus {
  status: string;
  heartbeat: number;
  queue_size: number;
  total_processed: number;
  last_update: string;
}

interface ZmqStatus {
  bind_url: string;
  socket_type: string;
  hwm: number;
  status: string;
  total_published: number;
  topics: string[];
  publish_rate: number;
  last_publish_time: string;
  subscriber_count: number;
  total_connections: number;
  total_disconnections: number;
  connection_events: Array<{ type: string; addr: string; time: string }>;
  note: string;
}

interface OverviewData {
  redis_ok: boolean;
  recorders: Record<string, RecorderStatus>;
}

const DashboardPage = () => {
  const [data, setData] = useState<OverviewData | null>(null);
  const [zmq, setZmq] = useState<ZmqStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const [overviewResult, zmqResult] = await Promise.all([
        api.getOverview(),
        api.getZmqStatus(),
      ]);
      setData(overviewResult as unknown as OverviewData);
      setZmq(zmqResult as unknown as ZmqStatus);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

  const formatTime = (ts: number) => {
    if (!ts) return '-';
    return new Date(ts * 1000).toLocaleTimeString();
  };

  const formatNum = (v: number) => {
    if (!v) return '0';
    return v.toLocaleString();
  };

  if (loading) {
    return (
      <PageWrapper>
        <Container>
          <div className='text-zinc-500'>加载中...</div>
        </Container>
      </PageWrapper>
    );
  }

  return (
    <PageWrapper>
      <Subheader>
        <SubheaderLeft>
          <div className='text-xl font-bold'>系统状态总览</div>
        </SubheaderLeft>
        <SubheaderRight>
          <Badge color={data?.redis_ok ? 'emerald' : 'red'} colorIntensity='500'>
            Redis: {data?.redis_ok ? '正常' : '不可用'}
          </Badge>
        </SubheaderRight>
      </Subheader>
      <Container>
        {error && (
          <Card className='mb-4 border border-red-500/50'>
            <CardBody>连接错误: {error}</CardBody>
          </Card>
        )}

        <div className='grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4'>
          {/* 录制器状态卡片 */}
          {data?.recorders &&
            Object.entries(data.recorders).map(([assetType, rec]) => (
              <Card key={assetType}>
                <CardBody>
                  <div className='mb-3 flex items-center justify-between'>
                    <span className='text-lg font-bold uppercase'>{assetType}</span>
                    <Badge
                      color={rec.status === 'running' ? 'emerald' : 'zinc'}
                      colorIntensity='500'>
                      {rec.status}
                    </Badge>
                  </div>
                  <div className='space-y-1 text-sm text-zinc-600 dark:text-zinc-400'>
                    <div className='flex justify-between'>
                      <span>队列积压</span>
                      <span className='font-mono font-bold text-blue-500'>{rec.queue_size}</span>
                    </div>
                    <div className='flex justify-between'>
                      <span>已处理</span>
                      <span className='font-mono'>{formatNum(rec.total_processed)}</span>
                    </div>
                    <div className='flex justify-between'>
                      <span>最新行情</span>
                      <span className='font-mono'>{rec.last_update || '-'}</span>
                    </div>
                    <div className='flex justify-between'>
                      <span>心跳</span>
                      <span className='font-mono'>{formatTime(rec.heartbeat)}</span>
                    </div>
                  </div>
                </CardBody>
              </Card>
            ))}

          {/* ZMQ 监控卡片 */}
          {zmq && (
            <Card>
              <CardBody>
                <div className='mb-3 flex items-center justify-between'>
                  <span className='text-lg font-bold'>ZMQ</span>
                  <Badge
                    color={
                      zmq.status === 'active'
                        ? 'emerald'
                        : zmq.status === 'bound'
                          ? 'blue'
                          : zmq.status === 'closed'
                            ? 'zinc'
                            : 'red'
                    }
                    colorIntensity='500'>
                    {zmq.status}
                  </Badge>
                </div>
                <div className='space-y-1 text-sm text-zinc-600 dark:text-zinc-400'>
                  <div className='flex justify-between'>
                    <span>类型</span>
                    <span className='font-mono'>{zmq.socket_type}</span>
                  </div>
                  <div className='flex justify-between'>
                    <span>已发布</span>
                    <span className='font-mono font-bold text-blue-500'>
                      {formatNum(zmq.total_published)}
                    </span>
                  </div>
                  <div className='flex justify-between'>
                    <span>发布速率</span>
                    <span className='font-mono'>{zmq.publish_rate.toFixed(1)}/s</span>
                  </div>
                  <div className='flex justify-between'>
                    <span>当前连接</span>
                    <span className='font-mono font-bold text-green-500'>
                      {zmq.subscriber_count}
                    </span>
                  </div>
                  <div className='flex justify-between'>
                    <span>历史连接</span>
                    <span className='font-mono text-xs'>
                      连 {zmq.total_connections} / 断 {zmq.total_disconnections}
                    </span>
                  </div>
                  <div className='flex justify-between'>
                    <span>HWM</span>
                    <span className='font-mono'>{zmq.hwm}</span>
                  </div>
                  <div className='flex justify-between'>
                    <span>绑定地址</span>
                    <span className='font-mono text-xs'>{zmq.bind_url}</span>
                  </div>
                  <div className='flex justify-between'>
                    <span>主题数</span>
                    <span className='font-mono'>{zmq.topics.length}</span>
                  </div>
                </div>
              </CardBody>
            </Card>
          )}
        </div>

        {/* ZMQ 主题列表 */}
        {zmq && zmq.topics.length > 0 && (
          <Card className='mt-4'>
            <CardBody>
              <div className='mb-2 text-sm font-bold'>ZMQ 发布主题 ({zmq.topics.length})</div>
              <div className='flex flex-wrap gap-2'>
                {zmq.topics.map((topic) => (
                  <span
                    key={topic}
                    className='rounded bg-zinc-100 px-2 py-1 font-mono text-xs dark:bg-zinc-800'>
                    {topic}
                  </span>
                ))}
              </div>
            </CardBody>
          </Card>
        )}

        {/* ZMQ 连接事件 */}
        {zmq && zmq.connection_events && zmq.connection_events.length > 0 && (
          <Card className='mt-4'>
            <CardBody>
              <div className='mb-2 text-sm font-bold'>
                ZMQ 连接事件 (当前 {zmq.subscriber_count} 个订阅者)
              </div>
              <div className='overflow-x-auto'>
                <table className='w-full text-xs'>
                  <thead className='border-b border-zinc-200 dark:border-zinc-700'>
                    <tr className='text-left text-zinc-500'>
                      <th className='px-2 py-1'>时间</th>
                      <th className='px-2 py-1'>事件</th>
                      <th className='px-2 py-1'>客户端地址</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...zmq.connection_events].reverse().map((evt, i) => (
                      <tr key={i} className='border-b border-zinc-100 dark:border-zinc-800'>
                        <td className='px-2 py-1 font-mono'>{evt.time}</td>
                        <td className='px-2 py-1'>
                          <span
                            className={`rounded px-1.5 py-0.5 text-xs ${
                              evt.type === 'CONNECTED'
                                ? 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300'
                                : 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300'
                            }`}>
                            {evt.type}
                          </span>
                        </td>
                        <td className='px-2 py-1 font-mono'>{evt.addr}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className='mt-2 text-xs text-zinc-400'>{zmq.note}</div>
            </CardBody>
          </Card>
        )}

        {!data?.recorders || Object.keys(data.recorders).length === 0 ? (
          <Card>
            <CardBody>
              <div className='py-8 text-center text-zinc-500'>
                暂无录制器运行中。请在交易日盘前启动行情引擎。
              </div>
            </CardBody>
          </Card>
        ) : null}
      </Container>
    </PageWrapper>
  );
};

export default DashboardPage;
