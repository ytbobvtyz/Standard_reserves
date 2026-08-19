import api from './client'
import type { ApiSuccess, LoginData, RefreshData, User } from './types'

export const authApi = {
  login: (username: string, password: string) =>
    api.post<ApiSuccess<LoginData>>('/auth/login', { username, password }),

  logout: () => api.post<{ status: string; message: string }>('/auth/logout'),

  refresh: (refreshToken: string) =>
    api.post<ApiSuccess<RefreshData>>('/auth/refresh', {
      refresh_token: refreshToken,
    }),

  profile: () => api.get<ApiSuccess<User>>('/auth/profile'),

  changePassword: (oldPassword: string, newPassword: string) =>
    api.post<{ status: string; message: string }>('/auth/change-password', {
      old_password: oldPassword,
      new_password: newPassword,
    }),
}
