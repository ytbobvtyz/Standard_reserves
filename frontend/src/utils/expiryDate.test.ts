import { describe, expect, it } from 'vitest'
import dayjs from 'dayjs'
import {
  EXPIRY_HINT,
  defaultExpiryDate,
  isExpiryTooFar,
  isExpiryTooSoon,
  maxExpiryDate,
  minExpiryDate,
} from './expiryDate'

describe('expiryDate', () => {
  it('keeps the default date at six months', () => {
    expect(defaultExpiryDate().startOf('day').isSame(dayjs().add(6, 'month').startOf('day'))).toBe(
      true,
    )
  })

  it('rejects dates earlier than three months', () => {
    expect(isExpiryTooSoon(dayjs().add(2, 'month'))).toBe(true)
    expect(isExpiryTooSoon(minExpiryDate())).toBe(false)
  })

  it('rejects dates later than six months', () => {
    expect(isExpiryTooFar(dayjs().add(7, 'month'))).toBe(true)
    expect(isExpiryTooFar(maxExpiryDate())).toBe(false)
  })

  it('shows the 3–6 month hint', () => {
    expect(EXPIRY_HINT).toContain('3 месяца')
    expect(EXPIRY_HINT).toContain('6 месяцев')
  })
})
