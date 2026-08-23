import React, { useEffect, useState } from 'react';
import PageWrapper from '../../components/layouts/PageWrapper/PageWrapper';
import Container from '../../components/layouts/Container/Container';
import Subheader, { SubheaderLeft } from '../../components/layouts/Subheader/Subheader';
import Card, { CardBody } from '../../components/ui/Card';
import Badge from '../../components/ui/Badge';
import api from '../../api';

interface ConfigData {
  gateways: string[];
  ctp: {
    md_front_address: string;
    subscribe_exchanges: string[];
    subscribe_asset_types: string[];
  };
  mysql: {
    host: string;
    port: number;
    user: string;
    password: string;
    database: string;
  };
  redis: {
    host: string;
    port: number;
    password: string;
    db: number;
  };
  zmq: {
    bind_url: string;
  };
  data: {
    dir: string;
  };
}

const ConfigPage = () => {
  const [config, setConfig] = useState<ConfigData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const result = await api.getConfig();
        setConfig(result as unknown as ConfigData);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading || !config) {
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
          <div className='text-xl font-bold'>配置查看</div>
        </SubheaderLeft>
      </Subheader>
      <Container>
        <div className='grid grid-cols-1 gap-4 md:grid-cols-2'>
          {/* 网关 */}
          <Card>
            <CardBody>
              <div className='mb-3 text-lg font-bold'>行情网关</div>
              <div className='space-y-2 text-sm'>
                <div className='flex justify-between'>
                  <span className='text-zinc-500'>启用网关</span>
                  <span className='font-mono'>{config.gateways.join(', ')}</span>
                </div>
                <div className='flex justify-between'>
                  <span className='text-zinc-500'>CTP 前置地址</span>
                  <span className='font-mono text-xs'>{config.ctp.md_front_address}</span>
                </div>
                <div className='flex justify-between'>
                  <span className='text-zinc-500'>订阅交易所</span>
                  <span className='font-mono text-xs'>
                    {config.ctp.subscribe_exchanges.join(', ')}
                  </span>
                </div>
                <div className='flex justify-between'>
                  <span className='text-zinc-500'>资产类型</span>
                  <span className='font-mono'>
                    {config.ctp.subscribe_asset_types.join(', ')}
                  </span>
                </div>
              </div>
            </CardBody>
          </Card>

          {/* ZMQ + Data */}
          <Card>
            <CardBody>
              <div className='mb-3 text-lg font-bold'>广播与存储</div>
              <div className='space-y-2 text-sm'>
                <div className='flex justify-between'>
                  <span className='text-zinc-500'>ZMQ 广播地址</span>
                  <span className='font-mono text-xs'>{config.zmq.bind_url}</span>
                </div>
                <div className='flex justify-between'>
                  <span className='text-zinc-500'>落盘根目录</span>
                  <span className='font-mono text-xs'>{config.data.dir}</span>
                </div>
              </div>
            </CardBody>
          </Card>

          {/* MySQL */}
          <Card>
            <CardBody>
              <div className='mb-3 text-lg font-bold'>MySQL</div>
              <div className='space-y-2 text-sm'>
                <div className='flex justify-between'>
                  <span className='text-zinc-500'>地址</span>
                  <span className='font-mono'>
                    {config.mysql.host}:{config.mysql.port}
                  </span>
                </div>
                <div className='flex justify-between'>
                  <span className='text-zinc-500'>数据库</span>
                  <span className='font-mono'>{config.mysql.database}</span>
                </div>
                <div className='flex justify-between'>
                  <span className='text-zinc-500'>用户</span>
                  <span className='font-mono'>{config.mysql.user}</span>
                </div>
                <div className='flex justify-between'>
                  <span className='text-zinc-500'>密码</span>
                  <span className='font-mono'>{config.mysql.password}</span>
                </div>
              </div>
            </CardBody>
          </Card>

          {/* Redis */}
          <Card>
            <CardBody>
              <div className='mb-3 text-lg font-bold'>Redis</div>
              <div className='space-y-2 text-sm'>
                <div className='flex justify-between'>
                  <span className='text-zinc-500'>地址</span>
                  <span className='font-mono'>
                    {config.redis.host}:{config.redis.port}
                  </span>
                </div>
                <div className='flex justify-between'>
                  <span className='text-zinc-500'>DB</span>
                  <span className='font-mono'>{config.redis.db}</span>
                </div>
                <div className='flex justify-between'>
                  <span className='text-zinc-500'>密码</span>
                  <span className='font-mono'>{config.redis.password}</span>
                </div>
              </div>
            </CardBody>
          </Card>
        </div>

        <Card className='mt-4'>
          <CardBody>
            <div className='flex items-center gap-2 text-sm text-zinc-500'>
              <Badge color='amber' colorIntensity='500'>
                注意
              </Badge>
              <span>密码等敏感字段已脱敏，仅显示前 2 位字符。</span>
            </div>
          </CardBody>
        </Card>
      </Container>
    </PageWrapper>
  );
};

export default ConfigPage;
