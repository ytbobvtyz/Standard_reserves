import { create } from 'zustand'
import { authApi } from '../api/auth'
import {
  clearAuthStorage,
  persistAuth,
} from '../api/client'
import type { User } from '../api/types'

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refreshToken: () => Promise<void>
  fetchProfile: () => Promise<void>
}

function readStoredUser(): User | null {
  const raw = localStorage.getItem('user')
  if (!raw) {
    return null
  }
  try {
    return JSON.parse(raw) as User
  } catch {
    return null
  }
}

const savedToken = localStorage.getItem('token')

export const useAuthStore = create<AuthState>((set, get) => ({
  user: readStoredUser(),
  token: savedToken,
  isAuthenticated: Boolean(savedToken),
  isLoading: false,

  login: async (username: string, password: string) => {
    set({ isLoading: true })
    try {
      const { data } = await authApi.login(username, password)
      const payload = data.data
      persistAuth({
        accessToken: payload.access_token,
        refreshToken: payload.refresh_token,
        user: payload.user,
      })
      set({
        user: payload.user,
        token: payload.access_token,
        isAuthenticated: true,
        isLoading: false,
      })
    } catch (error) {
      set({ isLoading: false })
      throw error
    }
  },

  logout: async () => {
    try {
      if (get().token) {
        await authApi.logout()
      }
    } catch {
      // Local logout still proceeds if the API call fails.
    } finally {
      clearAuthStorage()
      set({
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
      })
    }
  },

  refreshToken: async () => {
    const refresh = localStorage.getItem('refresh_token')
    if (!refresh) {
      await get().logout()
      return
    }
    const { data } = await authApi.refresh(refresh)
    persistAuth({ accessToken: data.data.access_token })
    set({
      token: data.data.access_token,
      isAuthenticated: true,
    })
  },

  fetchProfile: async () => {
    const token = get().token ?? localStorage.getItem('token')
    if (!token) {
      return
    }
    try {
      const { data } = await authApi.profile()
      persistAuth({ accessToken: token, user: data.data })
      set({
        user: data.data,
        token,
        isAuthenticated: true,
      })
    } catch {
      // 401 is handled by the axios interceptor.
    }
  },
}))
