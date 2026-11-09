import { describe, expect, it } from 'vitest'
import {
  DEFAULT_COVERAGE_THRESHOLDS,
  compareCoverageRows,
  coverageContext,
  coverageLevel,
  coverageMonths,
  coverageSummary,
  formatCoverage,
  needsReview,
  stockAfterApproval,
} from './coverage'

const thresholds = DEFAULT_COVERAGE_THRESHOLDS

describe('coverage', () => {
  it('uses only the approved quantity for one-time and replacement', () => {
    expect(
      stockAfterApproval({
        requestType: 'one_time',
        autoComplete: false,
        quantity: 100,
        existingNz: 400,
      }),
    ).toBe(100)
    expect(
      stockAfterApproval({
        requestType: 'normative',
        autoComplete: true,
        quantity: 100,
        existingNz: 400,
      }),
    ).toBe(100)
  })

  it('adds the current normative when the request increases it', () => {
    expect(
      stockAfterApproval({
        requestType: 'normative',
        autoComplete: false,
        quantity: 100,
        existingNz: 400,
      }),
    ).toBe(500)
    expect(
      stockAfterApproval({
        requestType: 'normative',
        autoComplete: false,
        quantity: 100,
        existingNz: null,
      }),
    ).toBe(100)
  })

  it('returns months of cover or null when there are no sales', () => {
    expect(coverageMonths(1000, 500)).toBe(2)
    expect(coverageMonths(1000, null)).toBeNull()
    expect(coverageMonths(1000, 0)).toBeNull()
  })

  it('marks high, normal, low and missing sales', () => {
    expect(coverageLevel(2, thresholds)).toBe('high')
    expect(coverageLevel(4, thresholds)).toBe('normal')
    expect(coverageLevel(4.1, thresholds)).toBe('low')
    expect(coverageLevel(null, thresholds)).toBe('none')
    expect(needsReview(4, thresholds)).toBe(false)
    expect(needsReview(4.1, thresholds)).toBe(true)
    expect(needsReview(null, thresholds)).toBe(true)
  })

  it('formats one decimal with a Russian comma', () => {
    expect(formatCoverage(2)).toBe('2,0 мес')
    expect(formatCoverage(10)).toBe('10,0 мес')
    expect(formatCoverage(1.25)).toBe('1,3 мес')
    expect(formatCoverage(null)).toBe('нет реализации')
  })

  it('puts rows without sales and slow rows first', () => {
    expect(compareCoverageRows(null, 10, thresholds)).toBeLessThan(0)
    expect(compareCoverageRows(10, 2, thresholds)).toBeLessThan(0)
    expect(compareCoverageRows(2, 3, thresholds)).toBeGreaterThan(0)
  })

  it('counts rows that need review', () => {
    expect(coverageSummary(0, 3)).toBe('Позиции не требуют разбора')
    expect(coverageSummary(1, 3)).toBe('1 из 3 позиций требуют разбора')
  })

  it('adds a wider slice only for a row that needs review', () => {
    expect(
      coverageContext({
        stock: 1000,
        monthlySales: 100,
        warehouseMonthlySales: 2000,
        productMonthlySales: 5000,
        thresholds,
      }),
    ).toBe('На складе артикул уходит быстрее. Медленный только этот клиент.')
    expect(
      coverageContext({
        stock: 1000,
        monthlySales: 100,
        warehouseMonthlySales: 200,
        productMonthlySales: 150,
        thresholds,
      }),
    ).toBe('Артикул медленный на всех складах.')
    expect(
      coverageContext({
        stock: 1000,
        monthlySales: null,
        warehouseMonthlySales: 2000,
        productMonthlySales: 5000,
        thresholds,
      }),
    ).toBe('У клиента нет реализации. На складе артикул уходит быстрее.')
    expect(
      coverageContext({
        stock: 1000,
        monthlySales: 500,
        warehouseMonthlySales: 200,
        productMonthlySales: 150,
        thresholds,
      }),
    ).toBeNull()
  })
})
