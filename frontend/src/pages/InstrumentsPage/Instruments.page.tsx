import React, { useEffect, useState, useMemo } from 'react';
import PageWrapper from '../../components/layouts/PageWrapper/PageWrapper';
import Container from '../../components/layouts/Container/Container';
import Subheader, { SubheaderLeft, SubheaderRight } from '../../components/layouts/Subheader/Subheader';
import Card, { CardBody } from '../../components/ui/Card';
import Badge from '../../components/ui/Badge';
import api from '../../api';

interface FutureInstrument {
  symbol: string;
  exchange: string;
  name: string;
  product_id: string;
  multiplier: number;
  tick_size: number;
  has_night_session: boolean;
  delivery_date: string | null;
  delivery_month: number | null;
  list_date: string | null;
  delist_date: string | null;
  margin_rate: number | null;
  fee_type: string;
  open_fee: number | null;
  close_fee: number | null;
  close_today_fee: number | null;
  future_type: string;
}

interface OptionInstrument {
  symbol: string;
  exchange: string;
  name: string;
  underlying: string;
  contract_type: string; // 'C' / 'P'
  strike_price: number;
  multiplier: number;
  tick_size: number;
  delivery_month: number | null;
  expiry_date: string | null;
  list_date: string | null;
  delist_date: string | null;
}

interface SummaryData {
  future: Record<string, number>;
  future_by_type: Record<string, number>;
  option: Record<string, number>;
  total: number;
}

const FUTURE_TYPE_LABELS: Record<string, string> = {
  STOCK_INDEX: '股指期货',
  BOND: '国债期货',
  COMMODITY: '商品期货',
};

const FUTURE_TYPE_COLORS: Record<string, string> = {
  STOCK_INDEX: 'red',
  BOND: 'blue',
  COMMODITY: 'emerald',
};

// 导出 CSV（带 UTF-8 BOM，Excel 可直接打开）
const exportCSV = (data: FutureInstrument[], filename: string) => {
  const headers = [
    '合约代码', '交易所', '分类', '品种', '合约名称',
    '乘数', '最小变动价位', '夜盘', '交割日', '交割月',
    '上市日', '摘牌日', '保证金率', '手续费类型', '开仓手续费', '平仓手续费', '平今手续费',
  ];
  const rows = data.map((d) => [
    d.symbol, d.exchange, FUTURE_TYPE_LABELS[d.future_type] || d.future_type,
    d.product_id, d.name,
    d.multiplier, d.tick_size, d.has_night_session ? '是' : '否',
    d.delivery_date || '', d.delivery_month || '',
    d.list_date || '', d.delist_date || '',
    d.margin_rate ?? '', d.fee_type,
    d.open_fee ?? '', d.close_fee ?? '', d.close_today_fee ?? '',
  ]);
  const csv = [headers, ...rows]
    .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(','))
    .join('\n');
  const bom = '\uFEFF';
  const blob = new Blob([bom + csv], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
};

const InstrumentsPage = () => {
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [instruments, setInstruments] = useState<FutureInstrument[] | OptionInstrument[]>([]);
  const [tab, setTab] = useState<'summary' | 'future' | 'option'>('summary');
  const [loading, setLoading] = useState(true);

  // 过滤
  const [futureType, setFutureType] = useState<string>('ALL');
  const [exchange, setExchange] = useState<string>('ALL');
  const [searchText, setSearchText] = useState<string>('');

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

  // 过滤后的合约
  const filteredInstruments = useMemo(() => {
    let result = instruments as any[];
    if (tab === 'future') {
      if (futureType !== 'ALL') {
        result = result.filter((i) => i.future_type === futureType);
      }
      if (exchange !== 'ALL') {
        result = result.filter((i) => i.exchange === exchange);
      }
    }
    if (searchText.trim()) {
      const q = searchText.trim().toUpperCase();
      result = result.filter(
        (i) =>
          i.symbol?.toUpperCase().includes(q) ||
          i.product_id?.toUpperCase().includes(q) ||
          i.underlying?.toUpperCase().includes(q) ||
          (i.name || '').includes(searchText.trim()),
      );
    }
    return result;
  }, [instruments, futureType, exchange, searchText, tab]);

  const exchanges = useMemo(() => {
    if (tab !== 'future') return [];
    return [...new Set(instruments.map((i) => i.exchange))].sort();
  }, [instruments, tab]);

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
                onClick={() => {
                  setTab(t);
                  setFutureType('ALL');
                  setExchange('ALL');
                  setSearchText('');
                }}
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
          <div className='space-y-4'>
            {/* 期货分类卡片 */}
            <div className='grid grid-cols-1 gap-4 md:grid-cols-3'>
              {Object.entries(FUTURE_TYPE_LABELS).map(([key, label]) => (
                <Card key={key}>
                  <CardBody>
                    <div className='flex items-center justify-between'>
                      <div>
                        <div className='text-sm text-zinc-500'>{label}</div>
                        <div className='text-2xl font-bold'>
                          {summary.future_by_type?.[key] || 0}
                        </div>
                      </div>
                      <Badge color={FUTURE_TYPE_COLORS[key] as any} colorIntensity='500'>
                        {key}
                      </Badge>
                    </div>
                  </CardBody>
                </Card>
              ))}
            </div>

            {/* 交易所汇总表 */}
            <Card>
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
            <CardBody className='p-0'>
              {/* 过滤栏 */}
              {tab === 'future' && (
                <div className='flex flex-wrap items-center gap-3 border-b p-3'>
                  <div className='flex gap-1'>
                    <button
                      onClick={() => setFutureType('ALL')}
                      className={`rounded px-3 py-1 text-sm ${
                        futureType === 'ALL'
                          ? 'bg-blue-500 text-white'
                          : 'bg-zinc-200 dark:bg-zinc-700'
                      }`}>
                      全部
                    </button>
                    {Object.entries(FUTURE_TYPE_LABELS).map(([key, label]) => (
                      <button
                        key={key}
                        onClick={() => setFutureType(key)}
                        className={`rounded px-3 py-1 text-sm ${
                          futureType === key
                            ? 'bg-blue-500 text-white'
                            : 'bg-zinc-200 dark:bg-zinc-700'
                        }`}>
                        {label}
                      </button>
                    ))}
                  </div>

                  <select
                    value={exchange}
                    onChange={(e) => setExchange(e.target.value)}
                    className='rounded border border-zinc-300 bg-white px-2 py-1 text-sm dark:border-zinc-600 dark:bg-zinc-800'>
                    <option value='ALL'>全部交易所</option>
                    {exchanges.map((ex) => (
                      <option key={ex} value={ex}>
                        {ex}
                      </option>
                    ))}
                  </select>

                  <input
                    type='text'
                    placeholder='搜索合约/品种/名称...'
                    value={searchText}
                    onChange={(e) => setSearchText(e.target.value)}
                    className='rounded border border-zinc-300 bg-white px-3 py-1 text-sm dark:border-zinc-600 dark:bg-zinc-800'
                  />

                  <div className='ml-auto flex items-center gap-3'>
                    <span className='text-sm text-zinc-500'>
                      {filteredInstruments.length} 个合约
                    </span>
                    <button
                      onClick={() =>
                        exportCSV(filteredInstruments, `future_instruments_${Date.now()}.csv`)
                      }
                      className='rounded bg-green-600 px-3 py-1 text-sm text-white hover:bg-green-700'>
                      导出 CSV
                    </button>
                  </div>
                </div>
              )}

              {tab === 'option' && (
                <div className='flex flex-wrap items-center gap-3 border-b p-3'>
                  <input
                    type='text'
                    placeholder='搜索合约/标的/名称...'
                    value={searchText}
                    onChange={(e) => setSearchText(e.target.value)}
                    className='rounded border border-zinc-300 bg-white px-3 py-1 text-sm dark:border-zinc-600 dark:bg-zinc-800'
                  />
                  <div className='ml-auto flex items-center gap-3'>
                    <span className='text-sm text-zinc-500'>
                      {filteredInstruments.length} 个合约
                    </span>
                  </div>
                </div>
              )}

              {/* 表格 */}
              <div className='overflow-x-auto'>
                <table className='w-full text-sm'>
                  <thead className='border-b border-zinc-200 dark:border-zinc-700'>
                    <tr className='text-left text-zinc-500'>
                      {tab === 'future' ? (
                        <>
                          <th className='px-3 py-2'>分类</th>
                          <th className='px-3 py-2'>合约代码</th>
                          <th className='px-3 py-2'>品种</th>
                          <th className='px-3 py-2'>名称</th>
                          <th className='px-3 py-2'>交易所</th>
                          <th className='px-3 py-2 text-right'>乘数</th>
                          <th className='px-3 py-2 text-right'>最小变动</th>
                          <th className='px-3 py-2'>夜盘</th>
                          <th className='px-3 py-2'>交割日</th>
                          <th className='px-3 py-2'>摘牌日</th>
                          <th className='px-3 py-2 text-right'>保证金率</th>
                        </>
                      ) : (
                        <>
                          <th className='px-3 py-2'>合约代码</th>
                          <th className='px-3 py-2'>交易所</th>
                          <th className='px-3 py-2'>类型</th>
                          <th className='px-3 py-2'>标的</th>
                          <th className='px-3 py-2 text-right'>行权价</th>
                          <th className='px-3 py-2 text-right'>乘数</th>
                          <th className='px-3 py-2'>到期日</th>
                          <th className='px-3 py-2'>摘牌日</th>
                        </>
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {loading ? (
                      <tr>
                        <td colSpan={tab === 'future' ? 11 : 8} className='py-8 text-center text-zinc-400'>
                          加载中...
                        </td>
                      </tr>
                    ) : filteredInstruments.length === 0 ? (
                      <tr>
                        <td colSpan={tab === 'future' ? 11 : 8} className='py-8 text-center text-zinc-400'>
                          暂无数据
                        </td>
                      </tr>
                    ) : (
                      filteredInstruments.map((inst: any) => (
                        <tr
                          key={`${inst.exchange}-${inst.symbol}`}
                          className='border-b border-zinc-100 hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-800/50'>
                          {tab === 'future' ? (
                            <>
                              <td className='px-3 py-2'>
                                <Badge
                                  color={FUTURE_TYPE_COLORS[inst.future_type] as any}
                                  colorIntensity='500'
                                  className='text-xs'>
                                  {FUTURE_TYPE_LABELS[inst.future_type] || inst.future_type}
                                </Badge>
                              </td>
                              <td className='px-3 py-2 font-mono font-bold'>{inst.symbol}</td>
                              <td className='px-3 py-2 font-mono'>{inst.product_id}</td>
                              <td className='px-3 py-2'>{inst.name}</td>
                              <td className='px-3 py-2'>{inst.exchange}</td>
                              <td className='px-3 py-2 text-right font-mono'>{inst.multiplier}</td>
                              <td className='px-3 py-2 text-right font-mono'>{inst.tick_size}</td>
                              <td className='px-3 py-2'>
                                {inst.has_night_session ? (
                                  <span className='text-green-600'>是</span>
                                ) : (
                                  <span className='text-zinc-400'>否</span>
                                )}
                              </td>
                              <td className='px-3 py-2 font-mono text-xs'>{inst.delivery_date || '-'}</td>
                              <td className='px-3 py-2 font-mono text-xs'>{inst.delist_date || '-'}</td>
                              <td className='px-3 py-2 text-right font-mono'>
                                {inst.margin_rate ? `${(inst.margin_rate * 100).toFixed(1)}%` : '-'}
                              </td>
                            </>
                          ) : (
                            <>
                              <td className='px-3 py-2 font-mono font-bold'>{inst.symbol}</td>
                              <td className='px-3 py-2'>{inst.exchange}</td>
                              <td className='px-3 py-2'>
                                <span className={`rounded px-2 py-0.5 text-xs ${
                                  inst.contract_type === 'C'
                                    ? 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300'
                                    : 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300'
                                }`}>
                                  {inst.contract_type === 'C' ? '认购' : '认沽'}
                                </span>
                              </td>
                              <td className='px-3 py-2 font-mono text-xs'>{inst.underlying || '-'}</td>
                              <td className='px-3 py-2 text-right font-mono'>{inst.strike_price || '-'}</td>
                              <td className='px-3 py-2 text-right font-mono'>{inst.multiplier || '-'}</td>
                              <td className='px-3 py-2 font-mono text-xs'>{inst.expiry_date || '-'}</td>
                              <td className='px-3 py-2 font-mono text-xs'>{inst.delist_date || '-'}</td>
                            </>
                          )}
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </CardBody>
          </Card>
        )}
      </Container>
    </PageWrapper>
  );
};

export default InstrumentsPage;
