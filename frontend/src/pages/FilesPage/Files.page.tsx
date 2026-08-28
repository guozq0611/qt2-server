import React, { useEffect, useState } from 'react';
import PageWrapper from '../../components/layouts/PageWrapper/PageWrapper';
import Container from '../../components/layouts/Container/Container';
import Subheader, { SubheaderLeft, SubheaderRight } from '../../components/layouts/Subheader/Subheader';
import Card, { CardBody } from '../../components/ui/Card';
import api from '../../api';

interface FileInfo {
  filename: string;
  size_bytes: number;
  size_mb: number;
  record_count: number;
  modified: string;
}

interface FilesStats {
  future: { file_count: number; total_size_mb: number; total_records: number };
  option: { file_count: number; total_size_mb: number; total_records: number };
  stock_option: { file_count: number; total_size_mb: number; total_records: number };
}

interface DirectoryInfo {
  name: string;
  label: string;
  is_current: boolean;
}

const FilesPage = () => {
  const [stats, setStats] = useState<FilesStats | null>(null);
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [directories, setDirectories] = useState<DirectoryInfo[]>([]);
  const [assetType, setAssetType] = useState('future');
  const [selectedDir, setSelectedDir] = useState('current');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const result = await api.getFilesStats();
        setStats(result as unknown as FilesStats);
      } catch (err) {
        console.error(err);
      }
    };
    fetchStats();
  }, []);

  // 加载目录列表
  useEffect(() => {
    const fetchDirs = async () => {
      try {
        const result = await api.getFilesDirectories(assetType);
        const dirs = (result as any).directories || [];
        setDirectories(dirs);
        // 如果当前选的目录不在列表里，切到 current
        if (dirs.length > 0 && !dirs.find((d: DirectoryInfo) => d.name === selectedDir)) {
          setSelectedDir('current');
        }
      } catch (err) {
        console.error(err);
      }
    };
    fetchDirs();
  }, [assetType]);

  // 加载文件列表
  useEffect(() => {
    const fetchFiles = async () => {
      try {
        const result = await api.getFilesList(assetType, selectedDir);
        setFiles((result as any).files || []);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchFiles();
  }, [assetType, selectedDir]);

  return (
    <PageWrapper>
      <Subheader>
        <SubheaderLeft>
          <div className='text-xl font-bold'>落盘文件</div>
        </SubheaderLeft>
        <SubheaderRight>
          <div className='flex gap-2'>
            <button
              onClick={() => {
                setAssetType('future');
                setSelectedDir('current');
              }}
              className={`rounded px-3 py-1 text-sm ${
                assetType === 'future' ? 'bg-blue-500 text-white' : 'bg-zinc-200 dark:bg-zinc-700'
              }`}>
              期货
            </button>
            <button
              onClick={() => {
                setAssetType('option');
                setSelectedDir('current');
              }}
              className={`rounded px-3 py-1 text-sm ${
                assetType === 'option' ? 'bg-blue-500 text-white' : 'bg-zinc-200 dark:bg-zinc-700'
              }`}>
              期权
            </button>
            <button
              onClick={() => {
                setAssetType('stock_option');
                setSelectedDir('current');
              }}
              className={`rounded px-3 py-1 text-sm ${
                assetType === 'stock_option' ? 'bg-blue-500 text-white' : 'bg-zinc-200 dark:bg-zinc-700'
              }`}>
              股票期权
            </button>
          </div>
        </SubheaderRight>
      </Subheader>
      <Container>
        {/* 统计卡片 */}
        {stats && (
          <div className='mb-4 grid grid-cols-1 gap-4 md:grid-cols-3'>
            {(['future', 'option', 'stock_option'] as const).map((type) => {
              const label = type === 'future' ? '期货' : type === 'option' ? '期权' : '股票期权';
              return (
              <Card key={type}>
                <CardBody>
                  <div className='mb-2 text-lg font-bold'>{label}</div>
                  <div className='grid grid-cols-3 gap-2 text-sm'>
                    <div>
                      <div className='text-zinc-500'>文件数</div>
                      <div className='font-mono text-lg font-bold text-blue-500'>
                        {stats[type].file_count}
                      </div>
                    </div>
                    <div>
                      <div className='text-zinc-500'>总大小</div>
                      <div className='font-mono text-lg font-bold'>{stats[type].total_size_mb} MB</div>
                    </div>
                    <div>
                      <div className='text-zinc-500'>总记录数</div>
                      <div className='font-mono text-lg font-bold'>
                        {stats[type].total_records.toLocaleString()}
                      </div>
                    </div>
                  </div>
                </CardBody>
              </Card>
              );
            })}
          </div>
        )}

        {/* 目录选择 + 文件列表 */}
        <Card>
          <CardBody className='p-4'>
            {/* 目录下拉框 */}
            <div className='mb-4 flex items-center gap-3'>
              <span className='text-sm text-zinc-500'>目录</span>
              <select
                value={selectedDir}
                onChange={(e) => setSelectedDir(e.target.value)}
                className='rounded border border-zinc-300 bg-white px-3 py-1 text-sm dark:border-zinc-600 dark:bg-zinc-800'>
                {directories.length === 0 ? (
                  <option value='current'>current</option>
                ) : (
                  directories.map((d) => (
                    <option key={d.name} value={d.name}>
                      {d.is_current ? `${d.label} (current)` : d.label}
                    </option>
                  ))
                )}
              </select>
              <span className='text-xs text-zinc-400'>
                {selectedDir === 'current'
                  ? '当前交易日实时写入'
                  : '历史归档（可导入数据库）'}
              </span>
            </div>
          </CardBody>
          <CardBody className='overflow-x-auto p-0'>
            <table className='w-full text-sm'>
              <thead className='border-b border-zinc-200 dark:border-zinc-700'>
                <tr className='text-left text-zinc-500'>
                  <th className='px-3 py-2'>文件名</th>
                  <th className='px-3 py-2 text-right'>大小</th>
                  <th className='px-3 py-2 text-right'>记录数</th>
                  <th className='px-3 py-2'>修改时间</th>
                </tr>
              </thead>
              <tbody>
                {files.length === 0 ? (
                  <tr>
                    <td colSpan={4} className='py-8 text-center text-zinc-400'>
                      暂无落盘文件
                    </td>
                  </tr>
                ) : (
                  files.map((f) => (
                    <tr
                      key={f.filename}
                      className='border-b border-zinc-100 hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-800/50'>
                      <td className='px-3 py-2 font-mono text-xs'>{f.filename}</td>
                      <td className='px-3 py-2 text-right font-mono'>{f.size_mb} MB</td>
                      <td className='px-3 py-2 text-right font-mono'>
                        {f.record_count.toLocaleString()}
                      </td>
                      <td className='px-3 py-2 font-mono text-xs text-zinc-500'>{f.modified}</td>
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

export default FilesPage;
