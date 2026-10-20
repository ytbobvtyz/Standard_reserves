import { describe, expect, it } from 'vitest'
import { axisWidthForLabels } from './NzByDepartmentChart'
import { chartRowsForTopClients, OTHERS_BAR_COLOR } from './TopClientsChart'
import { TOP_WAREHOUSE_COLORS } from './warehouseTrendColors'

describe('dashboard chart layout', () => {
  it('reserves enough axis width for a long department name', () => {
    const name = 'Управление продаж по дальневосточному федеральному округу'
    const width = axisWidthForLabels([name, 'Короткое'])
    expect(width).toBeGreaterThan(name.length * 7)
  })

  it('keeps others last in the horizontal chart and paints them gray', () => {
    const rows = chartRowsForTopClients([
      { client_id: 'a', client_code: 1, client_name: 'Крупный', nz_quantity: 2 },
      { client_id: 'b', client_code: 2, client_name: 'Средний', nz_quantity: 1 },
      { client_name: 'Остальные', nz_quantity: 9, is_other: true },
    ])
    expect(rows[0]).toMatchObject({ client: 'Остальные', isOther: true, nz: 9 })
    expect(rows.at(-1)?.client).toBe('1 · Крупный')
    expect(OTHERS_BAR_COLOR).toBe('#9CA3AF')
    expect(TOP_WAREHOUSE_COLORS[0]).toBe('#1677ff')
  })
})
