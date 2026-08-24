import apiClient from './client';

// ===== 监控 =====
export const getOverview = () => apiClient.get('/monitor/overview');
export const getLatestTicks = (assetType: string, limit = 100) =>
  apiClient.get(`/monitor/ticks/${assetType}?limit=${limit}`);
export const getAllTicks = (limit = 50) => apiClient.get(`/monitor/ticks?limit=${limit}`);
export const getZmqStatus = () => apiClient.get('/monitor/zmq');

// ===== 合约 =====
export const getFutureInstruments = (params?: {
  exchange?: string;
  future_type?: string;
  product_id?: string;
}) => apiClient.get('/instruments/future', { params: params || {} });
export const getFutureProducts = () => apiClient.get('/instruments/future/products');
export const getOptionInstruments = (exchange?: string) =>
  apiClient.get('/instruments/option', { params: exchange ? { exchange } : {} });
export const getInstrumentsSummary = () => apiClient.get('/instruments/summary');

// ===== 文件 =====
export const getFilesList = (assetType: string, date?: string) =>
  apiClient.get('/files/list', { params: { asset_type: assetType, date } });
export const getFilesStats = () => apiClient.get('/files/stats');

// ===== 配置 =====
export const getConfig = () => apiClient.get('/config/');

export default {
  getOverview,
  getLatestTicks,
  getAllTicks,
  getZmqStatus,
  getFutureInstruments,
  getFutureProducts,
  getOptionInstruments,
  getInstrumentsSummary,
  getFilesList,
  getFilesStats,
  getConfig,
};
