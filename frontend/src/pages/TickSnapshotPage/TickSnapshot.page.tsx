import React, { useEffect, useState, useMemo } from 'react';
import PageWrapper from '../../components/layouts/PageWrapper/PageWrapper';
import Container from '../../components/layouts/Container/Container';
import Subheader, { SubheaderLeft, SubheaderRight } from '../../components/layouts/Subheader/Subheader';
import Card, { CardBody } from '../../components/ui/Card';
import Badge from '../../components/ui/Badge';
import api from '../../api';

interface TickData {
  symbol: string;
  trade_date?: number;
  last_price?: number;
  volume?: number;
  turnover?: number;
  open_interest?: number;
  bid_price_1?: number;
  bid_volume_1?: number;
  ask_price_1?: number;
  ask_volume_1?: number;
  update_time?: string;
  // 期权专属
  underlying?: string;
  strike?: number;
  type?: string; // 'C' / 'P'
  delta?: number;
  implied_vol?: number;
  [key: string]: any;
}

interface ProductInfo {
  product_id: string;
  exchange: string;
  future_type: string;
  name: string;
  count: number;
}

// 从合约代码提取品种前缀（字母部分）
const extractProduct = (symbol: string): string => {
  const match = symbol.match(/^([a-zA-Z]+)/);
  return match ? match[1].toUpperCase() : '';
};

// 格式化时间: trade_date=20260824, update_time="112953.545" → "20260824 11:29:53.545"
const formatTime = (tradeDate?: number, updateTime?: string): string => {
  if (!tradeDate || !updateTime) return '-';
  const dateStr = String(tradeDate);
  // update_time: "HHMMSS.NNN" or "HHMMSS"
  const ut = updateTime;
  let hh, mm, ss, nnn;
  if (ut.includes('.')) {
    const [hms, ns] = ut.split('.');
    hh = hms.substring(0, 2);
    mm = hms.substring(2, 4);
    ss = hms.substring(4, 6);
    nnn = ns.padEnd(3, '0').substring(0, 3);
  } else {
    hh = ut.substring(0, 2);
    mm = ut.substring(2, 4);
    ss = ut.substring(4, 6);
    nnn = '000';
  }
  return `${dateStr} ${hh}:${mm}:${ss}.${nnn}`;
};

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

const OPTION_TYPE_LABELS: Record<string, string> = {
  INDEX_OPTION: '股指期权',
  COMMODITY_OPTION: '商品期权',
  STOCK_OPTION: '股票期权',
};

interface OptionProductInfo {
  product_id: string;
  exchange: string;
  option_type: string;
  name: string;
  count: number;
}

// 从期权合约代码提取品种前缀（字母部分）
const extractOptionProduct = (symbol: string): string => {
  const match = symbol.match(/^([a-zA-Z]+)/);
  return match ? match[1].toUpperCase() : '';
};

// 根据交易所判断期权分类
const classifyOption = (exchange: string): string => {
  if (exchange === 'CFFEX') return 'INDEX_OPTION';
  if (exchange === 'SSE' || exchange === 'SZSE') return 'STOCK_OPTION';
  return 'COMMODITY_OPTION';
};

const TickSnapshotPage = () => {
  const [ticks, setTicks] = useState<TickData[]>([]);
  const [products, setProducts] = useState<ProductInfo[]>([]);
  const [optionProducts, setOptionProducts] = useState<OptionProductInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [count, setCount] = useState(0);

  // 资产类型 tab: 'future' | 'option'
  const [assetType, setAssetType] = useState<'future' | 'option'>('future');

  // 过滤状态
  const [futureType, setFutureType] = useState<string>('ALL');
  const [selectedProduct, setSelectedProduct] = useState<string>('ALL');
  const [optionType, setOptionType] = useState<string>('ALL');
  const [selectedOptionProduct, setSelectedOptionProduct] = useState<string>('ALL');
  const [searchSymbol, setSearchSymbol] = useState<string>('');

  // 获取品种列表（用于分类和过滤）
  useEffect(() => {
    const fetchProducts = async () => {
      try {
        const [futureResult, optionResult] = await Promise.all([
          api.getFutureProducts(),
          api.getOptionProducts(),
        ]);
        setProducts((futureResult as any).products || []);
        setOptionProducts((optionResult as any).products || []);
      } catch (err) {
        console.error(err);
      }
    };
    fetchProducts();
  }, []);

  const fetchData = async () => {
    try {
      const result = await api.getLatestTicks(assetType, 500);
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

  // 构建 symbol → future_type 映射
  const symbolTypeMap = useMemo(() => {
    const map: Record<string, string> = {};
    for (const p of products) {
      map[p.product_id.toUpperCase()] = p.future_type;
    }
    return map;
  }, [products]);

  // 根据 product_id 获取 future_type
  const getFutureType = (symbol: string): string => {
    const pid = extractProduct(symbol);
    return symbolTypeMap[pid] || 'COMMODITY';
  };

  // 过滤后的 ticks
  const filteredTicks = useMemo(() => {
    let result = ticks;
    if (assetType === 'future') {
      if (futureType !== 'ALL') {
        result = result.filter((t) => getFutureType(t.symbol) === futureType);
      }
      if (selectedProduct !== 'ALL') {
        result = result.filter(
          (t) => extractProduct(t.symbol) === selectedProduct,
        );
      }
    } else {
      // 期权过滤
      if (optionType !== 'ALL') {
        result = result.filter((t) => {
          const ex = (t as any).exchange || '';
          return classifyOption(ex) === optionType;
        });
      }
      if (selectedOptionProduct !== 'ALL') {
        result = result.filter(
          (t) => extractOptionProduct(t.symbol) === selectedOptionProduct,
        );
      }
    }
    if (searchSymbol.trim()) {
      const q = searchSymbol.trim().toUpperCase();
      result = result.filter((t) => t.symbol.toUpperCase().includes(q));
    }
    return result;
  }, [ticks, assetType, futureType, selectedProduct, optionType, selectedOptionProduct, searchSymbol, symbolTypeMap]);

  // 按品种过滤选项
  const productOptions = useMemo(() => {
    if (futureType === 'ALL') return products;
    return products.filter((p) => p.future_type === futureType);
  }, [products, futureType]);

  // 期权品种过滤选项
  const optionProductOptions = useMemo(() => {
    if (optionType === 'ALL') return optionProducts;
    return optionProducts.filter((p) => p.option_type === optionType);
  }, [optionProducts, optionType]);

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
            {(['future', 'option'] as const).map((t) => (
              <button
                key={t}
                onClick={() => {
                  setAssetType(t);
                  setFutureType('ALL');
                  setSelectedProduct('ALL');
                  setOptionType('ALL');
                  setSelectedOptionProduct('ALL');
                  setSearchSymbol('');
                }}
                className={`rounded px-3 py-1 text-sm ${
                  assetType === t ? 'bg-blue-500 text-white' : 'bg-zinc-200 dark:bg-zinc-700'
                }`}>
                {t === 'future' ? '期货' : '期权'}
              </button>
            ))}
            <span className='text-sm text-zinc-500'>每 2 秒自动刷新</span>
          </div>
        </SubheaderRight>
      </Subheader>
      <Container>
        {/* 过滤栏 */}
        <Card className='mb-4'>
          <CardBody>
            <div className='flex flex-wrap items-center gap-3'>
              {assetType === 'future' && (
                <>
                  {/* 期货分类 */}
                  <div className='flex gap-1'>
                    <button
                      onClick={() => {
                        setFutureType('ALL');
                        setSelectedProduct('ALL');
                      }}
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
                        onClick={() => {
                          setFutureType(key);
                          setSelectedProduct('ALL');
                        }}
                        className={`rounded px-3 py-1 text-sm ${
                          futureType === key
                            ? 'bg-blue-500 text-white'
                            : 'bg-zinc-200 dark:bg-zinc-700'
                        }`}>
                        {label}
                      </button>
                    ))}
                  </div>

                  {/* 品种过滤 */}
                  <select
                    value={selectedProduct}
                    onChange={(e) => setSelectedProduct(e.target.value)}
                    className='rounded border border-zinc-300 bg-white px-2 py-1 text-sm dark:border-zinc-600 dark:bg-zinc-800'>
                    <option value='ALL'>全部品种</option>
                    {productOptions.map((p) => (
                      <option key={p.product_id} value={p.product_id}>
                        {p.product_id} ({p.name}) - {FUTURE_TYPE_LABELS[p.future_type]}
                      </option>
                    ))}
                  </select>
                </>
              )}

              {assetType === 'option' && (
                <>
                  {/* 期权分类 */}
                  <div className='flex gap-1'>
                    <button
                      onClick={() => {
                        setOptionType('ALL');
                        setSelectedOptionProduct('ALL');
                      }}
                      className={`rounded px-3 py-1 text-sm ${
                        optionType === 'ALL'
                          ? 'bg-blue-500 text-white'
                          : 'bg-zinc-200 dark:bg-zinc-700'
                      }`}>
                      全部
                    </button>
                    {Object.entries(OPTION_TYPE_LABELS).map(([key, label]) => (
                      <button
                        key={key}
                        onClick={() => {
                          setOptionType(key);
                          setSelectedOptionProduct('ALL');
                        }}
                        className={`rounded px-3 py-1 text-sm ${
                          optionType === key
                            ? 'bg-blue-500 text-white'
                            : 'bg-zinc-200 dark:bg-zinc-700'
                        }`}>
                        {label}
                      </button>
                    ))}
                  </div>

                  {/* 期权品种过滤 */}
                  <select
                    value={selectedOptionProduct}
                    onChange={(e) => setSelectedOptionProduct(e.target.value)}
                    className='rounded border border-zinc-300 bg-white px-2 py-1 text-sm dark:border-zinc-600 dark:bg-zinc-800'>
                    <option value='ALL'>全部品种</option>
                    {optionProductOptions.map((p) => (
                      <option key={p.product_id} value={p.product_id}>
                        {p.product_id} ({p.name}) - {OPTION_TYPE_LABELS[p.option_type]}
                      </option>
                    ))}
                  </select>
                </>
              )}

              {/* 合约搜索 */}
              <input
                type='text'
                placeholder='搜索合约代码...'
                value={searchSymbol}
                onChange={(e) => setSearchSymbol(e.target.value)}
                className='rounded border border-zinc-300 bg-white px-3 py-1 text-sm dark:border-zinc-600 dark:bg-zinc-800'
              />

              <div className='ml-auto text-sm text-zinc-500'>
                显示 {filteredTicks.length} / {count} 个合约
              </div>
            </div>
          </CardBody>
        </Card>

        {/* 行情表格 */}
        <Card>
          <CardBody className='overflow-x-auto p-0'>
            <table className='w-full text-sm'>
              <thead className='border-b border-zinc-200 dark:border-zinc-700'>
                <tr className='text-left text-zinc-500'>
                  {assetType === 'future' ? (
                    <>
                      <th className='px-3 py-2'>分类</th>
                      <th className='px-3 py-2'>合约代码</th>
                      <th className='px-3 py-2 text-right'>最新价</th>
                      <th className='px-3 py-2 text-right'>成交量</th>
                      <th className='px-3 py-2 text-right'>持仓量</th>
                      <th className='px-3 py-2 text-right'>买一价</th>
                      <th className='px-3 py-2 text-right'>买一量</th>
                      <th className='px-3 py-2 text-right'>卖一价</th>
                      <th className='px-3 py-2 text-right'>卖一量</th>
                      <th className='px-3 py-2'>更新时间</th>
                    </>
                  ) : (
                    <>
                      <th className='px-3 py-2'>合约代码</th>
                      <th className='px-3 py-2'>类型</th>
                      <th className='px-3 py-2'>标的</th>
                      <th className='px-3 py-2 text-right'>行权价</th>
                      <th className='px-3 py-2 text-right'>最新价</th>
                      <th className='px-3 py-2 text-right'>成交量</th>
                      <th className='px-3 py-2 text-right'>持仓量</th>
                      <th className='px-3 py-2 text-right'>买一价</th>
                      <th className='px-3 py-2 text-right'>卖一价</th>
                      <th className='px-3 py-2'>更新时间</th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={10} className='py-8 text-center text-zinc-400'>
                      加载中...
                    </td>
                  </tr>
                ) : filteredTicks.length === 0 ? (
                  <tr>
                    <td colSpan={10} className='py-8 text-center text-zinc-400'>
                      暂无行情数据（非交易时段或引擎未运行）
                    </td>
                  </tr>
                ) : (
                  filteredTicks.map((tick) => {
                    if (assetType === 'future') {
                      const ft = getFutureType(tick.symbol);
                      return (
                        <tr
                          key={tick.symbol}
                          className='border-b border-zinc-100 hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-800/50'>
                          <td className='px-3 py-2'>
                            <Badge
                              color={FUTURE_TYPE_COLORS[ft] as any}
                              colorIntensity='500'
                              className='text-xs'>
                              {FUTURE_TYPE_LABELS[ft]}
                            </Badge>
                          </td>
                          <td className='px-3 py-2 font-mono font-bold'>{tick.symbol}</td>
                          <td className='px-3 py-2 text-right font-mono text-blue-500'>
                            {formatPrice(tick.last_price)}
                          </td>
                          <td className='px-3 py-2 text-right font-mono'>
                            {formatNum(tick.volume)}
                          </td>
                          <td className='px-3 py-2 text-right font-mono'>
                            {formatNum(tick.open_interest)}
                          </td>
                          <td className='px-3 py-2 text-right font-mono'>
                            {formatPrice(tick.bid_price_1)}
                          </td>
                          <td className='px-3 py-2 text-right font-mono'>
                            {tick.bid_volume_1 ?? '-'}
                          </td>
                          <td className='px-3 py-2 text-right font-mono'>
                            {formatPrice(tick.ask_price_1)}
                          </td>
                          <td className='px-3 py-2 text-right font-mono'>
                            {tick.ask_volume_1 ?? '-'}
                          </td>
                          <td className='px-3 py-2 font-mono text-xs text-zinc-500'>
                            {formatTime(tick.trade_date, tick.update_time)}
                          </td>
                        </tr>
                      );
                    }
                    // 期权行
                    return (
                      <tr
                        key={tick.symbol}
                        className='border-b border-zinc-100 hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-800/50'>
                        <td className='px-3 py-2 font-mono font-bold'>{tick.symbol}</td>
                        <td className='px-3 py-2'>
                          <span className={`rounded px-2 py-0.5 text-xs ${
                            tick.type === 'C'
                              ? 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300'
                              : 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300'
                          }`}>
                            {tick.type === 'C' ? '购' : '沽'}
                          </span>
                        </td>
                        <td className='px-3 py-2 font-mono text-xs'>{tick.underlying || '-'}</td>
                        <td className='px-3 py-2 text-right font-mono'>
                          {tick.strike ? (tick.strike / 10000).toFixed(2) : '-'}
                        </td>
                        <td className='px-3 py-2 text-right font-mono text-blue-500'>
                          {formatPrice(tick.last_price)}
                        </td>
                        <td className='px-3 py-2 text-right font-mono'>
                          {formatNum(tick.volume)}
                        </td>
                        <td className='px-3 py-2 text-right font-mono'>
                          {formatNum(tick.open_interest)}
                        </td>
                        <td className='px-3 py-2 text-right font-mono'>
                          {formatPrice(tick.bid_price_1)}
                        </td>
                        <td className='px-3 py-2 text-right font-mono'>
                          {formatPrice(tick.ask_price_1)}
                        </td>
                        <td className='px-3 py-2 font-mono text-xs text-zinc-500'>
                          {formatTime(tick.trade_date, tick.update_time)}
                        </td>
                      </tr>
                    );
                  })
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
