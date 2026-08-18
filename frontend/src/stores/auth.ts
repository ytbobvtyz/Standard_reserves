import { create } from 'zustand'
import type { User } from '../types'

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const savedToken = localStorage.getItem('token')
const savedUser = localStorage.getItem('user')

export const useAuthStore = create<AuthState>((set) => ({
  user: savedUser ? (JSON.parse(savedUser) as User) : null,
  token: savedToken,
  isAuthenticated: Boolean(savedToken),
  isLoading: false,
  login: async (username: string) => {
    const mockUser: User = {
      id: 'dev-user',
      username,
      full_name: username,
      role: 'commercial',
      department: 'Отдел продаж',
    }
    const token = 'dev-token'
    localStorage.setItem('token', token)
    localStorage.setItem('user', JSON.stringify(mockUser))
    set({
      user: mockUser,
      token,
      isAuthenticated: true,
    })
  },
  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    set({ user: null, token: null, isAuthenticated: false })
  },
}))
