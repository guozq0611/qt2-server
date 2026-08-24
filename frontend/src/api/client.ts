import axios from 'axios';

// API 基础地址（vite dev proxy 会将 /api 代理到 FastAPI 后端）
const apiClient = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 响应拦截器：统一错误处理
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('[API Error]', error.message);
    return Promise.reject(error);
  },
);

export default apiClient;
