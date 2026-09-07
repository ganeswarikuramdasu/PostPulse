import axios from 'axios'
import type { ContentInput, PredictionResponse, HistoryResponse, ModelInfoResponse } from '../types'

const rawBaseUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8001/api').trim().replace(/\/+$/, '')
const API_BASE_URL = rawBaseUrl.endsWith('/api') ? rawBaseUrl : `${rawBaseUrl}/api`

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem('postpulse_token')
      delete client.defaults.headers.common['Authorization']
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export async function predictContent(payload: ContentInput): Promise<PredictionResponse> {
  const { data } = await client.post<PredictionResponse>('/predict', payload)
  return data
}

export async function fetchHistory(limit = 50, offset = 0): Promise<HistoryResponse> {
  const { data } = await client.get<HistoryResponse>('/prediction-history', { params: { limit, offset } })
  return data
}

export async function fetchPredictionDetail(id: number) {
  const { data } = await client.get(`/prediction-history/${id}`)
  return data
}

export async function fetchModelInfo(): Promise<ModelInfoResponse> {
  const { data } = await client.get<ModelInfoResponse>('/model-info')
  return data
}

export async function checkHealth(): Promise<boolean> {
  try {
    await client.get('/health')
    return true
  } catch {
    return false
  }
}

export async function verifyEmail(token: string) {
  const { data } = await client.get('/auth/verify-email', { params: { token } })
  return data
}

export async function resendVerification(email: string, password: string) {
  const { data } = await client.post('/auth/resend-verification', { email, password })
  return data
}

export default client
