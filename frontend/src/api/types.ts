export type UserRole = 'commercial' | 'pp' | 'economist' | 'logistics' | 'guest'

export interface User {
  id: string
  username: string
  full_name: string
  role: UserRole
  department?: string | null
  email?: string
  last_login_at?: string | null
}

export interface ApiSuccess<T> {
  status: 'success'
  data: T
  meta?: {
    page: number
    limit: number
    total: number
  }
}

export interface ApiErrorBody {
  status: 'error'
  error: {
    code: string
    message: string
    details?: Array<{ field?: string; message: string }>
  }
}

export interface LoginData {
  access_token: string
  refresh_token: string
  expires_in: number
  user: User
}

export interface RefreshData {
  access_token: string
  expires_in: number
}
