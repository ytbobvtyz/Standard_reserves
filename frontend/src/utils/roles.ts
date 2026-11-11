import type { UserRole } from '../api/types'

export const LOGISTICS_ACCESS: UserRole[] = ['logistics', 'admin']
export const CLIENT_EXCEL_ROLES: UserRole[] = ['logistics', 'economist']

export function hasLogisticsAccess(role?: UserRole | null): boolean {
  return role != null && LOGISTICS_ACCESS.includes(role)
}

export function canEditClients(role?: UserRole | null): boolean {
  return role != null && role !== 'guest'
}

export function canUploadClientsExcel(role?: UserRole | null): boolean {
  return role != null && CLIENT_EXCEL_ROLES.includes(role)
}
