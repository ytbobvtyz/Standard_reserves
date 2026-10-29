import type { Dayjs } from 'dayjs'
import type { StockDynamicsData, StockGranularity } from '../../api/types'
import { TOP_WAREHOUSE_COLORS } from '../dashboard/warehouseTrendColors'

export type { StockGranularity }

export const STOCK_NORMATIVE_COLOR = TOP_WAREHOUSE_COLORS[0]
export const STOCK_AVAILABLE_COLOR = TOP_WAREHOUSE_COLORS[1]
export const STOCK_AVAILABLE_MIN_COLOR = '#95de64'
export const STOCK_AVAILABLE_MAX_COLOR = '#237804'
export const STOCK_ACTUAL_COLOR = TOP_WAREHOUSE_COLORS[2]

export interface StockChartRow {
  date: string
  normative: number | null
  availableMin: number | null
  availableMedian: number | null
  availableMax: number | null
  actual: number | null
}

export interface StockChartModel {
  hasNormative: boolean
  showAvailableMin: boolean
  showAvailableLevel: boolean
  showAvailableMax: boolean
  showActual: boolean
  rows: StockChartRow[]
}

const INCLUSIVE_DAY_OFFSET = 89

export function defaultStockRange(
  granularity: StockGranularity,
  today: Dayjs,
  earliest?: string | null,
): { from: string; to: string } {
  const to = today.format('YYYY-MM-DD')
  if (granularity === 'day') {
    return { from: today.subtract(INCLUSIVE_DAY_OFFSET, 'day').format('YYYY-MM-DD'), to }
  }
  if (granularity === 'week') {
    return { from: today.subtract(1, 'year').format('YYYY-MM-DD'), to }
  }
  if (!earliest) {
    return { from: to, to }
  }
  if (earliest > to) {
    return { from: earliest, to: earliest }
  }
  return { from: earliest, to }
}

export function definedPointCount(values: Array<number | null>): number {
  return values.filter((value) => value != null).length
}

export function buildStockChartModel(data: StockDynamicsData): StockChartModel {
  const rows = data.dates.map((date, index) => ({
    date,
    normative: data.normative[index] ?? null,
    availableMin: data.available_min[index] ?? null,
    availableMedian: data.available_median[index] ?? null,
    availableMax: data.available_max[index] ?? null,
    actual: data.actual[index] ?? null,
  }))
  return {
    hasNormative: definedPointCount(data.normative) > 0,
    showAvailableMin: definedPointCount(data.available_min) > 0,
    showAvailableLevel: definedPointCount(data.available_median) > 0,
    showAvailableMax: definedPointCount(data.available_max) > 0,
    showActual: definedPointCount(data.actual) > 0,
    rows,
  }
}

export function formatStockPeriod(value: string, granularity: StockGranularity): string {
  const date = new Date(`${value}T00:00:00`)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  if (granularity === 'month') {
    return date.toLocaleDateString('ru-RU', { month: 'short', year: 'numeric' })
  }
  return date.toLocaleDateString('ru-RU')
}

export function formatTons(value: number): string {
  return new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  }).format(value)
}
