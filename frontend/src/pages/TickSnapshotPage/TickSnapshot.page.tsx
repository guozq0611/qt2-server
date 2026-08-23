import React, { useEffect, useState } from 'react';
import PageWrapper from '../../components/layouts/PageWrapper/PageWrapper';
import Container from '../../components/layouts/Container/Container';
import Subheader, { SubheaderLeft, SubheaderRight } from '../../components/layouts/Subheader/Subheader';
import Card, { CardBody } from '../../components/ui/Card';
import Badge from '../../components/ui/Badge';
import api from '../../api';

interface TickData {
  symbol: string;
  last_price?: number;
  volume?: number;
  turnover?: number;
  open_interest?: number;
  bid_price_1?: number;
  bid_volume_1?: number;
  ask_price_1?: number;
  ask_volume_1?: number;
  update_time?: string;
  [key: string]: any;
}

const TickSnapshotPage = () => {
  const [ticks, setTicks] = useState<TickData[]>([]);
  const [assetType, setAssetType] = useState('future');
  const [loading, setLoading] = useState(true);
  const [count, setCount] = useState(0);

  const fetchData = async () => {
    try {
      const result = await api.getLatestTicks(assetType, 200);
      setTicks((result as any).ticks || []);
      setCount((result as any).count || 0);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, [assetType]);

  const formatPrice = (v?: number) => {
    if (v === undefined || v === null) return '-';
    return (v / 10000).toFixed(2);
  };

  const formatNum = (v?: number) => {
    if (v === undefined || v === null) return '-';
    return v.toLocaleString();
  };

  return (
    <PageWrapper>
      <Subheader>
        <SubheaderLeft>
          <div className='text-xl font-bold'>行情快照</div>
        </SubheaderLeft>
        <SubheaderRight>
          <div className='flex gap-2'>
            <button
              onClick={() => setAssetType('future')}
              className={`rounded px-3 py-1 text-sm ${
                assetType === 'future'
                  ? 'bg-blue-500 text-white'
                  : 'bg-zinc-200 dark:bg-zinc-700'
              }`}>
              期货
            </button>
            <button
              onClick={() => setAssetType('option')}
              className={`rounded px-3 py-1 text-sm ${
                assetType === 'option'
                  ? 'bg-blue-500 text-white'
                  : 'bg-zinc-200 dark:bg-zinc-700'
              }`}>
              期权
            </button>
          </div>
        </SubheaderRight>
      </Subheader>
      <Container>
        <Card className='mb-4'>
          <CardBody>
            <div className='flex items-center justify-between text-sm text-zinc-500'>
              <span>共 {count} 个合约</span>
              <span>每 2 秒自动刷新</span>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody className='overflow-x-auto p-0'>
            <table className='w-full text-sm'>
              <thead className='border-b border-zinc-200 dark:border-zinc-700'>
                <tr className='text-left text-zinc-500'>
                  <th className='px-3 py-2'>合约代码</th>
                  <th className='px-3 py-2 text-right'>最新价</th>
                  <th className='px-3 py-2 text-right'>成交量</th>
                  <th className='px-3 py-2 text-right'>持仓量</th>
                  <th className='px-3 py-2 text-right'>买一价</th>
                  <th className='px-3 py-2 text-right'>买一量</th>
                  <th className='px-3 py-2 text-right'>卖一价</th>
                  <th className='px-3 py-2 text-right'>卖一量</th>
                  <th className='px-3 py-2'>更新时间</th>
                </tr>
              </thead>
              <tbody>
                {ticks.length === 0 ? (
                  <tr>
                    <td colSpan={9} className='py-8 text-center text-zinc-400'>
                      暂无行情数据（非交易时段或引擎未运行）
                    </td>
                  </tr>
                ) : (
                  ticks.map((tick) => (
                    <tr
                      key={tick.symbol}
                      className='border-b border-zinc-100 hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-800/50'>
                      <td className='px-3 py-2 font-mono font-bold'>{tick.symbol}</td>
                      <td className='px-3 py-2 text-right font-mono text-blue-500'>
                        {formatPrice(tick.last_price)}
                      </td>
                      <td className='px-3 py-2 text-right font-mono'>{formatNum(tick.volume)}</td>
                      <td className='px-3 py-2 text-right font-mono'>
                        {formatNum(tick.open_interest)}
                      </td>
                      <td className='px-3 py-2 text-right font-mono'>
                        {formatPrice(tick.bid_price_1)}
                      </td>
                      <td className='px-3 py-2 text-right font-mono'>{tick.bid_volume_1 ?? '-'}</td>
                      <td className='px-3 py-2 text-right font-mono'>
                        {formatPrice(tick.ask_price_1)}
                      </td>
                      <td className='px-3 py-2 text-right font-mono'>{tick.ask_volume_1 ?? '-'}</td>
                      <td className='px-3 py-2 font-mono text-zinc-500'>{tick.update_time ?? '-'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </CardBody>
        </Card>
      </Container>
    </PageWrapper>
  );
};

export default TickSnapshotPage;
