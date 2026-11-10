import type { UserRole } from '../api/types'

export const LOGISTICS_ACCESS: UserRole[] = ['logistics', 'admin']

export function hasLogisticsAccess(role?: UserRole | null): boolean {
  return role != null && LOGISTICS_ACCESS.includes(role)
}
