import { describe, expect, it } from 'vitest'
import { convertDeficitToKg, orderRouteKey, routeTotalKg } from './b2b'
import type { GeneratedOrder } from '../api/types'

describe('b2b conversion', () => {
  it('converts pieces to kilograms using weight_kg', () => {
    expect(convertDeficitToKg(400, 'шт', 0.25)).toBe(100)
  })

  it('converts tons to kilograms', () => {
    expect(convertDeficitToKg(0.5, 'т', 0.25)).toBe(500)
  })

  it('keeps kilograms as kilograms', () => {
    expect(convertDeficitToKg(80, 'кг', 0.25)).toBe(80)
  })

  it('sums route deficit in kilograms', () => {
    const route: GeneratedOrder = {
      plant_code: 1001,
      plant_name: 'Завод Московский',
      warehouse_code: 2001,
      warehouse_name: 'Склад Ростов',
      estimated_delivery_days: 5,
      items: [
        {
          product_code: 10001,
          product_name: 'Подшипник',
          deficit: 400,
          unit: 'шт',
          weight_kg: 0.25,
        },
        {
          product_code: 10002,
          product_name: 'Корпус',
          deficit: 200,
          unit: 'шт',
          weight_kg: 2.5,
        },
      ],
    }
    expect(orderRouteKey(route)).toBe('1001-2001')
    expect(routeTotalKg(route)).toBe(600)
  })
})
