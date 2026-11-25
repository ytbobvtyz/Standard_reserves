import { describe, expect, it } from 'vitest'
import { chartBlocked, compareClientCoverage, toggleCode } from './clientAnalytics'

describe('compareClientCoverage', () => {
  const row = (
    label: string,
    outside: boolean,
    coverage: number | null,
    normative = 1,
  ) => ({
    label,
    outside_normative: outside,
    coverage_months: coverage,
    normative_tons: normative,
  })

  it('puts consumption without a normative first, then dead stock, then the thickest coverage', () => {
    const rows = [
      row('Короткий', false, 1),
      row('Толстый', false, 8),
      row('Без продаж', false, null, 5),
      row('Без норматива', true, 0),
    ]
    const labels = [...rows].sort(compareClientCoverage).map((item) => item.label)
    expect(labels).toEqual(['Без норматива', 'Без продаж', 'Толстый', 'Короткий'])
  })
})

describe('chart selection', () => {
  it('returns null when the last cleared code is selected again', () => {
    expect(toggleCode([10], [10, 20], 20, true)).toBeNull()
  })

  it('blocks the chart when either table is fully cleared', () => {
    expect(chartBlocked(2, [], 3, null)).toBe(true)
    expect(chartBlocked(2, null, 3, [])).toBe(true)
    expect(chartBlocked(0, null, 2, null)).toBe(false)
  })
})
