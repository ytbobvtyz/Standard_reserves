import type { UserRole } from '../../api/types'

export const ROLE_OPTIONS: Array<{ value: UserRole; label: string }> = [
  { value: 'commercial', label: 'Коммерция' },
  { value: 'pp', label: 'ПП' },
  { value: 'economist', label: 'Экономист' },
  { value: 'logistics', label: 'Логист' },
  { value: 'guest', label: 'Наблюдатель' },
]

export const ROLE_LABEL: Record<UserRole, string> = {
  commercial: 'Коммерция',
  pp: 'ПП',
  economist: 'Экономист',
  logistics: 'Логист',
  guest: 'Наблюдатель',
}
