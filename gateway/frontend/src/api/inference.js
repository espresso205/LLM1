import axios from 'axios'

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
})

// 请求拦截器：预留 Bearer Token 位置
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：统一错误格式
http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const msg =
      err.response?.data?.detail ||
      err.response?.data?.message ||
      err.message ||
      '请求失败'
    return Promise.reject(new Error(msg))
  }
)

/**
 * 提交推理请求
 * @param {{ prompt: string, max_tokens: number, temperature: number }} payload
 * @returns {Promise<{ request_id: string, result: string }>}
 */
export function submitInference(payload) {
  return http.post('/inference', payload)
}

/**
 * 获取历史记录列表
 * @param {{ limit?: number, offset?: number, status?: string }} params
 * @returns {Promise<{ items: Array, total: number }>}
 */
export function fetchHistory(params = {}) {
  return http.get('/history', { params })
}

/**
 * 获取单条记录详情
 * @param {string} requestId
 * @returns {Promise<object>}
 */
export function fetchInferenceDetail(requestId) {
  return http.get(`/history/${requestId}`)
}
