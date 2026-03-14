import axios from 'axios'
import { ElMessage } from 'element-plus'

const http = axios.create({
  baseURL: '/api',
  timeout: 120000
})

http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const detail = error.response?.data?.detail
    const msg = Array.isArray(detail)
      ? detail.map((d) => d?.msg || String(d)).filter(Boolean).join('; ')
      : detail || error.message || '请求失败'
    ElMessage.error(msg)
    return Promise.reject(new Error(msg))
  }
)

export const healthCheck = () => http.get('/health')
export const getModels = () => http.get('/models')
export const updateSettings = (data) => http.post('/settings', data)

export const inferSingle = (file, onUploadProgress) => {
  const fd = new FormData()
  fd.append('file', file)
  return http.post('/infer', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress
  })
}

export const inferBatch = (files, onUploadProgress) => {
  const fd = new FormData()
  files.forEach((f) => fd.append('files', f))
  return http.post('/infer/batch', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress
  })
}

export const getTaskStatus = (taskId) => http.get(`/tasks/${taskId}`)

export const getHistory = (page = 1, pageSize = 20) =>
  http.get('/history', { params: { page, page_size: pageSize } })

export const getHistoryDetail = (id) => http.get(`/history/${id}`)
