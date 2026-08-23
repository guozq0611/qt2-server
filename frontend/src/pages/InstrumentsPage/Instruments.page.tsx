import React, { useEffect, useState } from 'react';
import PageWrapper from '../../components/layouts/PageWrapper/PageWrapper';
import Container from '../../components/layouts/Container/Container';
import Subheader, { SubheaderLeft, SubheaderRight } from '../../components/layouts/Subheader/Subheader';
import Card, { CardBody } from '../../components/ui/Card';
import api from '../../api';

interface Instrument {
  symbol: string;
  exchange: string;
  asset_type: string;
}

interface SummaryData {
  future: Record<string, number>;
  option: Record<string, number>;
  total: number;
}

const InstrumentsPage = () => {
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [tab, setTab] = useState<'summary' | 'future' | 'option'>('summary');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        if (tab === 'summary') {
          const result = await api.getInstrumentsSummary();
          setSummary(result as unknown as SummaryData);
        } else if (tab === 'future') {
          const result = await api.getFutureInstruments();
          setInstruments((result as any).instruments || []);
        } else if (tab === 'option') {
          const result = await api.getOptionInstruments();
          setInstruments((result as any).instruments || []);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [tab]);

  return (
    <PageWrapper>
      <Subheader>
        <SubheaderLeft>
          <div className='text-xl font-bold'>合约列表</div>
        </SubheaderLeft>
        <SubheaderRight>
          <div className='flex gap-2'>
            {(['summary', 'future', 'option'] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`rounded px-3 py-1 text-sm ${
                  tab === t ? 'bg-blue-500 text-white' : 'bg-zinc-200 dark:bg-zinc-700'
                }`}>
                {t === 'summary' ? '汇总' : t === 'future' ? '期货' : '期权'}
              </button>
            ))}
          </div>
        </SubheaderRight>
      </Subheader>
      <Container>
        {tab === 'summary' && summary ? (
          <div className='grid grid-cols-1 gap-4 md:grid-cols-3'>
            <Card className='col-span-3'>
              <CardBody>
                <div className='mb-4 text-lg font-bold'>合约数量汇总</div>
                <table className='w-full text-sm'>
                  <thead className='border-b'>
                    <tr className='text-left text-zinc-500'>
                      <th className='py-2'>交易所</th>
                      <th className='py-2 text-right'>期货</th>
                      <th className='py-2 text-right'>期权</th>
                      <th className='py-2 text-right'>合计</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.keys(summary.future).map((ex) => (
                      <tr key={ex} className='border-b border-zinc-100 dark:border-zinc-800'>
                        <td className='py-2 font-bold'>{ex}</td>
                        <td className='py-2 text-right font-mono'>{summary.future[ex]}</td>
                        <td className='py-2 text-right font-mono'>{summary.option[ex] || 0}</td>
                        <td className='py-2 text-right font-mono font-bold text-blue-500'>
                          {(summary.future[ex] || 0) + (summary.option[ex] || 0)}
                        </td>
                      </tr>
                    ))}
                    <tr className='font-bold'>
                      <td className='py-2'>总计</td>
                      <td className='py-2 text-right font-mono'>
                        {Object.values(summary.future).reduce((a, b) => a + b, 0)}
                      </td>
                      <td className='py-2 text-right font-mono'>
                        {Object.values(summary.option).reduce((a, b) => a + b, 0)}
                      </td>
                      <td className='py-2 text-right font-mono text-blue-500'>{summary.total}</td>
                    </tr>
                  </tbody>
                </table>
              </CardBody>
            </Card>
          </div>
        ) : (
          <Card>
            <CardBody className='overflow-x-auto p-0'>
              <div className='border-b p-3 text-sm text-zinc-500'>
                共 {instruments.length} 个合约
              </div>
              <table className='w-full text-sm'>
                <thead className='border-b border-zinc-200 dark:border-zinc-700'>
                  <tr className='text-left text-zinc-500'>
                    <th className='px-3 py-2'>合约代码</th>
                    <th className='px-3 py-2'>交易所</th>
                    <th className='px-3 py-2'>类型</th>
                  </tr>
                </thead>
                <tbody>
                  {instruments.map((inst) => (
                    <tr
                      key={`${inst.exchange}-${inst.symbol}`}
                      className='border-b border-zinc-100 hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-800/50'>
                      <td className='px-3 py-2 font-mono font-bold'>{inst.symbol}</td>
                      <td className='px-3 py-2'>{inst.exchange}</td>
                      <td className='px-3 py-2'>
                        <span className='rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'>
                          {inst.asset_type}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardBody>
          </Card>
        )}
      </Container>
    </PageWrapper>
  );
};

export default InstrumentsPage;
