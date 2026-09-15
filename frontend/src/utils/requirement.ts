export interface CoefficientParams {
  category_a: number
  category_b: number
  category_c: number
  remote_warehouse: number
}

export const DEFAULT_COEFFICIENTS: CoefficientParams = {
  category_a: 1,
  category_b: 1.5,
  category_c: 2,
  remote_warehouse: 1.5,
}

export function categoryFactor(
  category?: string | null,
  params: CoefficientParams = DEFAULT_COEFFICIENTS,
): number {
  const key = (category ?? '').trim().toUpperCase()
  if (key === 'A') return params.category_a
  if (key === 'B') return params.category_b
  if (key === 'C') return params.category_c
  return 1
}

export function distanceFactor(
  longDistance?: boolean | null,
  params: CoefficientParams = DEFAULT_COEFFICIENTS,
): number {
  return longDistance ? params.remote_warehouse : 1
}

export function calculateRequirement(
  quantity: number | null | undefined,
  category?: string | null,
  longDistance?: boolean | null,
  params: CoefficientParams = DEFAULT_COEFFICIENTS,
): number | null {
  if (quantity == null || Number.isNaN(Number(quantity))) {
    return null
  }
  const raw =
    Number(quantity) * categoryFactor(category, params) * distanceFactor(longDistance, params)
  return Number(raw.toFixed(32))
}

export function formatFactor(value: number): string {
  return value.toFixed(1).replace('.', ',')
}

export function formatRequirementQty(value: number): string {
  // Intl.NumberFormat supports at most 20 fractional digits in the target runtime.
  // The API keeps the authoritative Decimal value rounded to 32 places.
  return value.toLocaleString('ru-RU', { maximumFractionDigits: 20 })
}

export function categoryLabel(
  category?: string | null,
  params: CoefficientParams = DEFAULT_COEFFICIENTS,
): string {
  if (!category) {
    return '—'
  }
  const cat = category.trim().toUpperCase()
  return `${cat} (×${formatFactor(categoryFactor(cat, params))})`
}

export function distanceLabel(
  longDistance?: boolean | null,
  params: CoefficientParams = DEFAULT_COEFFICIENTS,
): string {
  if (longDistance == null) {
    return '—'
  }
  const factor = distanceFactor(longDistance, params)
  return longDistance ? `Да (×${formatFactor(factor)})` : `Нет (×${formatFactor(factor)})`
}

export function requirementTooltip(
  quantity: number,
  unit: string,
  category?: string | null,
  longDistance?: boolean | null,
  params: CoefficientParams = DEFAULT_COEFFICIENTS,
): string {
  const cat = (category ?? 'A').trim().toUpperCase() || 'A'
  const catF = categoryFactor(cat, params)
  const distF = distanceFactor(Boolean(longDistance), params)
  const result = calculateRequirement(quantity, cat, longDistance, params) ?? 0
  const distText = longDistance ? 'удалённый склад' : 'не удалённый склад'
  return `Расчёт: ${formatRequirementQty(quantity)} ${unit} × ${formatFactor(catF)} (категория ${cat}) × ${formatFactor(distF)} (${distText}) = ${formatRequirementQty(result)} ${unit}`
}
