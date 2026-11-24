import { describe, expect, it } from 'vitest'
import { relatedProductsTooltip } from './relatedSales'

describe('relatedProductsTooltip', () => {
  it('says there are no related articles', () => {
    expect(relatedProductsTooltip(undefined, 'avg_sales', 'т')).toBe(
      'Нет связанных артикулов',
    )
    expect(relatedProductsTooltip([], 'avg_sales', 'шт')).toBe(
      'Нет связанных артикулов',
    )
  })

  it('lists related articles in the column unit', () => {
    const products = [
      {
        code: 10004,
        name: 'Подшипник 6204ZZ-NEW',
        avg_sales: 25,
        avg_sales_warehouse: 10.2,
        avg_sales_all_warehouses: 40,
      },
      {
        code: 10006,
        name: 'Подшипник 6204ZZ-OLD',
        avg_sales: 15.126,
        avg_sales_warehouse: 4,
        avg_sales_all_warehouses: 8,
      },
    ]
    expect(relatedProductsTooltip(products, 'avg_sales', 'т')).toBe(
      [
        'Связанные артикулы:',
        '• 10004 — Подшипник 6204ZZ-NEW: 25.000',
        '• 10006 — Подшипник 6204ZZ-OLD: 15.126',
      ].join('\n'),
    )
    expect(relatedProductsTooltip(products, 'avg_sales_warehouse', 'шт')).toBe(
      [
        'Связанные артикулы:',
        '• 10004 — Подшипник 6204ZZ-NEW: 10',
        '• 10006 — Подшипник 6204ZZ-OLD: 4',
      ].join('\n'),
    )
  })
})
