import { describe, expect, it } from 'vitest'
import type { DashboardTrendSeries } from '../../api/types'
import { rankWarehouses, TOP_WAREHOUSE_COLORS } from './warehouseTrendColors'

function series(
  code: number,
  name: string,
  points: Array<[string, number]>,
): DashboardTrendSeries {
  return {
    key: `warehouse:${code}`,
    warehouse_code: code,
    warehouse_name: name,
    points: points.map(([period, total]) => ({
      period,
      total_normative: total,
      count_active: 1,
    })),
  }
}

describe('rankWarehouses', () => {
  const periods = ['2026-09-28', '2026-10-05', '2026-10-12']
  const today = new Date('2026-10-11T00:00:00')

  it('colors the top three warehouses by volume on the current date', () => {
    const legend = rankWarehouses(
      [
        series(1, 'Малый', [
          ['2026-09-28', 9000],
          ['2026-10-05', 10],
        ]),
        series(2, 'Средний', [['2026-10-05', 50]]),
        series(3, 'Крупный', [['2026-10-05', 80]]),
        series(4, 'Второй', [['2026-10-05', 70]]),
        series(5, 'Тихий', [['2026-10-05', 5]]),
      ],
      periods,
      today,
    )

    expect(legend.slice(0, 3).map((item) => item.warehouseName)).toEqual([
      'Крупный',
      'Второй',
      'Средний',
    ])
    expect(legend.slice(0, 3).map((item) => item.color)).toEqual([...TOP_WAREHOUSE_COLORS])
    const restColors = legend.slice(3).map((item) => item.color)
    expect(new Set(restColors).size).toBe(restColors.length)
    expect(restColors.every((color) => !TOP_WAREHOUSE_COLORS.includes(color as (typeof TOP_WAREHOUSE_COLORS)[number]))).toBe(true)
    expect(restColors.every((color) => !['#8c8c8c', '#bfbfbf', '#595959', '#d9d9d9'].includes(color))).toBe(true)
  })

  it('recalculates the top when the current volume changes', () => {
    const before = rankWarehouses(
      [series(1, 'А', [['2026-10-05', 10]]), series(2, 'Б', [['2026-10-05', 20]])],
      periods,
      today,
    )
    const after = rankWarehouses(
      [series(1, 'А', [['2026-10-05', 30]]), series(2, 'Б', [['2026-10-05', 20]])],
      periods,
      today,
    )
    expect(before[0].warehouseName).toBe('Б')
    expect(after[0].warehouseName).toBe('А')
    expect(after[0].color).toBe(TOP_WAREHOUSE_COLORS[0])
  })
})
