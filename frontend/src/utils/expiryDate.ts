import type { Dayjs } from 'dayjs'
import dayjs from 'dayjs'

export const MAX_EXPIRY_MONTHS = 6
export const EXPIRY_HINT = 'Максимальный срок — 6 месяцев от даты создания'
export const EXPIRY_ERROR = 'Срок не может превышать 6 месяцев от даты создания'

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
