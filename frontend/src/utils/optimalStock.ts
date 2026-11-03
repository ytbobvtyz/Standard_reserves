export type RequestUnit = 'шт' | 'т'

export function kgToRequestQuantity(
  kg: number,
  unit: RequestUnit,
  weightKg?: number | null,
): number | null {
  if (!Number.isFinite(kg) || kg <= 0) {
    return null
  }
  if (unit === 'т') {
    return Number((kg / 1000).toFixed(6))
  }
  if (weightKg == null || weightKg <= 0) {
    return null
  }
  return Number((kg / weightKg).toFixed(2))
}
