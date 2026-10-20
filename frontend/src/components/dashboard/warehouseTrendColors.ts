import type { DashboardTrendSeries } from '../../api/types'

export const TOP_WAREHOUSE_COLORS = ['#1677ff', '#52c41a', '#fa8c16'] as const
const PALE_WAREHOUSE_COLORS = [
  '#b37feb',
  '#5cdbd3',
  '#ff85c0',
  '#ffd666',
  '#85a5ff',
  '#d3adf7',
  '#ffadd2',
  '#87e8de',
  '#d3f261',
  '#ffbb96',
  '#69c0ff',
  '#b7eb8f',
] as const

export interface WarehouseVolume {
  warehouseCode: number
  warehouseName: string
  volume: number
}

export interface WarehouseLegendEntry extends WarehouseVolume {
  rank: number
  color: string
}

export function colorForRank(rank: number): string {
  if (rank < TOP_WAREHOUSE_COLORS.length) {
    return TOP_WAREHOUSE_COLORS[rank]
  }
  const paleIndex = (rank - TOP_WAREHOUSE_COLORS.length) % PALE_WAREHOUSE_COLORS.length
  return PALE_WAREHOUSE_COLORS[paleIndex]
}

export function rankWarehouseVolumes(items: WarehouseVolume[]): WarehouseLegendEntry[] {
  const ranked = [...items].sort((left, right) => {
    if (right.volume !== left.volume) {
      return right.volume - left.volume
    }
    return left.warehouseName.localeCompare(right.warehouseName, 'ru')
  })
  return ranked.map((item, index) => ({
    ...item,
    rank: index,
    color: colorForRank(index),
  }))
}

function periodOnCurrentDate(periods: string[], today: Date): string | undefined {
  const valid = periods.filter((period) => !Number.isNaN(new Date(`${period}T00:00:00`).getTime()))
  const notAfterToday = valid.filter(
    (period) => new Date(`${period}T00:00:00`) <= today,
  )
  if (notAfterToday.length > 0) {
    return notAfterToday[notAfterToday.length - 1]
  }
  return valid[0]
}

function volumeOnPeriod(series: DashboardTrendSeries[], period: string | undefined): Map<number, number> {
  const totals = new Map<number, number>()
  for (const item of series) {
    const point = period
      ? item.points.find((entry) => entry.period === period)
      : item.points[item.points.length - 1]
    const volume = point?.total_normative ?? 0
    totals.set(item.warehouse_code, (totals.get(item.warehouse_code) ?? 0) + volume)
  }
  return totals
}

export function rankWarehouses(
  series: DashboardTrendSeries[],
  periods: string[],
  today = new Date(),
): WarehouseLegendEntry[] {
  const period = periodOnCurrentDate(periods, today)
  const volumes = volumeOnPeriod(series, period)
  const names = new Map<number, string>()
  for (const item of series) {
    if (!names.has(item.warehouse_code)) {
      names.set(item.warehouse_code, item.warehouse_name)
    }
  }
  return rankWarehouseVolumes(
    [...volumes.entries()].map(([warehouseCode, volume]) => ({
      warehouseCode,
      warehouseName: names.get(warehouseCode) ?? String(warehouseCode),
      volume,
    })),
  )
}

export function colorForSeries(
  series: DashboardTrendSeries,
  legend: WarehouseLegendEntry[],
): string {
  return legend.find((item) => item.warehouseCode === series.warehouse_code)?.color ?? '#b37feb'
}
