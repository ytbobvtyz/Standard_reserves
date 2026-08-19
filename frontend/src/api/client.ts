import axios, { type AxiosError } from 'axios'
import type { ApiErrorBody } from './types'

const TOKEN_KEY = 'token'
const REFRESH_TOKEN_KEY = 'refresh_token'
const USER_KEY = 'user'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
})

function isAuthEndpoint(url?: string): boolean {
  if (!url) {
    return false
  }
  return url.includes('/auth/login') || url.includes('/auth/refresh')
}

export function getStoredAccessToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function persistAuth(payload: {
  accessToken: string
  refreshToken?: string
  user?: unknown
}): void {
  localStorage.setItem(TOKEN_KEY, payload.accessToken)
  if (payload.refreshToken) {
    localStorage.setItem(REFRESH_TOKEN_KEY, payload.refreshToken)
  }
  if (payload.user) {
    localStorage.setItem(USER_KEY, JSON.stringify(payload.user))
  }
}

export function clearAuthStorage(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const payload = error.response?.data as ApiErrorBody | undefined
    return payload?.error?.message ?? fallback
  }
  return fallback
}

api.interceptors.request.use((config) => {
  const token = getStoredAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401 && !isAuthEndpoint(error.config?.url)) {
      clearAuthStorage()
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export default api
