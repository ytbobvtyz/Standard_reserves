import type { GeneratedOrder, GeneratedOrderItem } from '../api/types'

export function orderRouteKey(order: GeneratedOrder): string {
  return `${order.plant_code}-${order.warehouse_code}`
}

export function convertDeficitToKg(
  deficit: number,
  unit: string,
  weightKg = 0,
): number {
  const normalized = unit.trim().toLowerCase().replace(/\./g, '')
  let kilograms = deficit
  if (normalized === 'шт' || normalized === 'штук') {
    kilograms = deficit * weightKg
  } else if (normalized === 'т' || normalized === 't' || normalized === 'тонн') {
    kilograms = deficit * 1000
  }
  return Math.round(kilograms * 100) / 100
}

export function itemDeficitKg(item: GeneratedOrderItem): number {
  return convertDeficitToKg(item.deficit, item.unit, item.weight_kg ?? 0)
}

export function routeTotalKg(order: GeneratedOrder): number {
  return Math.round(order.items.reduce((sum, item) => sum + itemDeficitKg(item), 0) * 100) /
    100
}

export function todayStamp(now = new Date()): string {
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}${month}${day}`
}
