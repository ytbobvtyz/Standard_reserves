import dayjs from 'dayjs'
import { describe, expect, it } from 'vitest'
import { TOP_WAREHOUSE_COLORS } from '../dashboard/warehouseTrendColors'
import {
  STOCK_ACTUAL_COLOR,
  STOCK_AVAILABLE_COLOR,
  STOCK_AVAILABLE_MAX_COLOR,
  STOCK_AVAILABLE_MIN_COLOR,
  STOCK_NORMATIVE_COLOR,
  buildStockChartModel,
  defaultStockRange,
} from './stockDynamics'

describe('defaultStockRange', () => {
  const today = dayjs('2026-10-28')

  it('uses the last 90 days for daily granularity', () => {
    const range = defaultStockRange('day', today)
    expect(range.to).toBe('2026-10-28')
    expect(today.diff(dayjs(range.from), 'day')).toBe(89)
  })

  it('uses the last year for weekly granularity', () => {
    expect(defaultStockRange('week', today)).toEqual({
      from: '2025-10-28',
      to: '2026-10-28',
    })
  })

  it('uses the first data date for monthly granularity', () => {
    expect(defaultStockRange('month', today, '2024-03-01')).toEqual({
      from: '2024-03-01',
      to: '2026-10-28',
    })
    expect(defaultStockRange('month', today, null)).toEqual({
      from: '2026-10-28',
      to: '2026-10-28',
    })
    expect(defaultStockRange('month', today, '2027-01-01')).toEqual({
      from: '2027-01-01',
      to: '2027-01-01',
    })
  })
})

describe('buildStockChartModel', () => {
  it('keeps monthly stock bands and period sales, including a single point', () => {
    const model = buildStockChartModel({
      dates: ['2026-10-01', '2026-10-02'],
      normative: [10, null],
      available_min: [4, 4],
      available_median: [8, 8],
      available_max: [10, 10],
      actual: [1.5, null],
      unit: 'т',
    })
    expect(model.hasNormative).toBe(true)
    expect(model.showAvailableMin).toBe(true)
    expect(model.showAvailableLevel).toBe(true)
    expect(model.showAvailableMax).toBe(true)
    expect(model.showActual).toBe(true)
    expect(model.rows[1]).toMatchObject({
      normative: null,
      availableMin: 4,
      availableMedian: 8,
      availableMax: 10,
      actual: null,
    })
  })

  it('hides the chart when every normative point is empty', () => {
    const model = buildStockChartModel({
      dates: ['2026-10-01', '2026-10-02'],
      normative: [null, null],
      available_min: [1, 2],
      available_median: [1, 2],
      available_max: [1, 2],
      actual: [1, 2],
      unit: 'т',
    })
    expect(model.hasNormative).toBe(false)
  })

  it('keeps only the daily stock line when the band is empty', () => {
    const model = buildStockChartModel({
      dates: ['2026-10-02', '2026-10-03'],
      normative: [1, 1],
      available_min: [null, null],
      available_median: [8, 0],
      available_max: [null, null],
      actual: [null, null],
      unit: 'т',
    })
    expect(model.showAvailableMin).toBe(false)
    expect(model.showAvailableMax).toBe(false)
    expect(model.showAvailableLevel).toBe(true)
    expect(model.showActual).toBe(false)
  })
})

describe('stock dynamics colors', () => {
  it('reuses the warehouse palette for the median and sales', () => {
    expect(STOCK_NORMATIVE_COLOR).toBe(TOP_WAREHOUSE_COLORS[0])
    expect(STOCK_AVAILABLE_COLOR).toBe('#52c41a')
    expect(STOCK_AVAILABLE_MIN_COLOR).toBe('#95de64')
    expect(STOCK_AVAILABLE_MAX_COLOR).toBe('#237804')
    expect(STOCK_ACTUAL_COLOR).toBe('#fa8c16')
  })
})
