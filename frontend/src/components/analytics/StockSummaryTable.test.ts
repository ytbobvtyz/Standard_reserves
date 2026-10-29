import { describe, expect, it } from 'vitest'
import type { StockMonthSummary } from '../../api/types'
import { averageColumn } from './StockSummaryTable'

const months: StockMonthSummary[] = [
  { month: '2026-08-01', available_median: null, actual: null, normative_avg: null },
  { month: '2026-09-01', available_median: 4, actual: 2, normative_avg: 11 },
  { month: '2026-10-01', available_median: 8, actual: 4, normative_avg: 16 },
]

describe('averageColumn', () => {
  it('averages only months that have a value', () => {
    expect(averageColumn(months, 'available_median')).toBe(6)
    expect(averageColumn(months, 'actual')).toBe(3)
    expect(averageColumn(months, 'normative_avg')).toBe(13.5)
  })

  it('returns null when every month is empty', () => {
    expect(
      averageColumn(
        [{ month: '2026-08-01', available_median: null, actual: null, normative_avg: null }],
        'actual',
      ),
    ).toBeNull()
  })
})
