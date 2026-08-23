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

interface OverviewData {
  redis_ok: boolean;
  recorders: Record<string, RecorderStatus>;
}

const DashboardPage = () => {
  const [data, setData] = useState<OverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const result = await api.getOverview();
      setData(result as unknown as OverviewData);
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
                      <span className='font-mono'>{rec.total_processed}</span>
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
        </div>

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
