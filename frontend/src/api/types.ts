export type UserRole = 'commercial' | 'pp' | 'economist' | 'logistics' | 'guest'

export interface User {
  id: string
  username: string
  full_name: string
  role: UserRole
  department?: string
}
