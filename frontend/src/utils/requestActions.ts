import type { RequestStatus } from '../api/types'

export const DELETABLE_STATUSES: RequestStatus[] = [
  'draft',
  'pp_approved',
  'economy_check',
  'rejected',
  'expired',
]

export const DELETE_CONFIRM = 'Вы уверены, что хотите удалить запрос?'

export function canDeleteByStatus(status: RequestStatus): boolean {
  return DELETABLE_STATUSES.includes(status)
}
