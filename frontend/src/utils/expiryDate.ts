import type { Dayjs } from 'dayjs'
import dayjs from 'dayjs'

export const MAX_EXPIRY_MONTHS = 6
export const EXPIRY_HINT = 'Максимальный срок — 6 месяцев от даты создания'
export const EXPIRY_ERROR = 'Срок не может превышать 6 месяцев от даты создания'
export const EXPIRY_TOO_LATE = 'Дата окончания не может быть позже текущей'
export const EXPIRY_IN_PAST = 'Дата окончания не может быть раньше сегодняшнего дня'
export const ECONOMY_EXPIRY_HINT =
  'Срок можно только уменьшить: не раньше сегодня и не позже текущей даты'
export const ACTIVE_EXPIRY_HINT =
  'Можно только уменьшить срок: от сегодня до текущей даты окончания'

export function maxExpiryDate(from?: string | Date | Dayjs | null): Dayjs {
  return dayjs(from ?? undefined).add(MAX_EXPIRY_MONTHS, 'month')
}

export function defaultExpiryDate(): Dayjs {
  return dayjs().add(MAX_EXPIRY_MONTHS, 'month')
}

export function isExpiryTooFar(
  value: Dayjs | null | undefined,
  from?: string | Date | Dayjs | null,
): boolean {
  if (!value) {
    return false
  }
  return value.startOf('day').isAfter(maxExpiryDate(from).startOf('day'))
}

export function isExpiryInPast(value: Dayjs | null | undefined): boolean {
  if (!value) {
    return false
  }
  return value.startOf('day').isBefore(dayjs().startOf('day'))
}

export function isExpiryAfterCurrent(
  value: Dayjs | null | undefined,
  currentExpiry?: string | Date | Dayjs | null,
): boolean {
  if (!value || !currentExpiry) {
    return false
  }
  return value.startOf('day').isAfter(dayjs(currentExpiry).startOf('day'))
}

export function isExpiryDecreaseInvalid(
  value: Dayjs | null | undefined,
  currentExpiry?: string | Date | Dayjs | null,
): boolean {
  return isExpiryInPast(value) || isExpiryAfterCurrent(value, currentExpiry)
}

export function expiryDecreaseError(
  value: Dayjs | null | undefined,
  currentExpiry?: string | Date | Dayjs | null,
): string | null {
  if (isExpiryInPast(value)) {
    return EXPIRY_IN_PAST
  }
  if (isExpiryAfterCurrent(value, currentExpiry)) {
    return EXPIRY_TOO_LATE
  }
  return null
}
