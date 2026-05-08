import axios, { type AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'
import type { ApiEnvelope } from '../types'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response: AxiosResponse) => {
    const payload = response.data as ApiEnvelope<unknown> | unknown

    if (
      payload &&
      typeof payload === 'object' &&
      'code' in payload &&
      'message' in payload
    ) {
      const envelope = payload as ApiEnvelope<unknown>

      if (envelope.code === 0) {
        return envelope.data
      }

      if (envelope.code === 401) {
        localStorage.removeItem('token')
        router.push('/login')
      } else {
        ElMessage.error(envelope.message || '请求失败')
      }

      return Promise.reject(new Error(envelope.message || '请求失败'))
    }

    return payload as AxiosResponse['data']
  },
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      router.push('/login')
      ElMessage.error('登录已过期，请重新登录')
      return Promise.reject(error)
    }

    const message =
      error.response?.data?.message || error.message || '网络请求失败'
    ElMessage.error(message)
    return Promise.reject(error)
  },
)

export default request
