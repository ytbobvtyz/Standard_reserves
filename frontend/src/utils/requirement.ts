const CATEGORY_FACTORS: Record<string, number> = { A: 1, B: 1.5, C: 2 }

export function categoryFactor(category?: string | null): number {
  const key = (category ?? '').trim().toUpperCase()
  return CATEGORY_FACTORS[key] ?? 1
}

export function distanceFactor(longDistance?: boolean | null): number {
  return longDistance ? 1.5 : 1
}

export function calculateRequirement(
  quantity: number | null | undefined,
  category?: string | null,
  longDistance?: boolean | null,
): number | null {
  if (quantity == null || Number.isNaN(Number(quantity))) {
    return null
  }
  const raw = Number(quantity) * categoryFactor(category) * distanceFactor(longDistance)
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

export function categoryLabel(category?: string | null): string {
  if (!category) {
    return '—'
  }
  const cat = category.trim().toUpperCase()
  return `${cat} (×${formatFactor(categoryFactor(cat))})`
}

export function distanceLabel(longDistance?: boolean | null): string {
  if (longDistance == null) {
    return '—'
  }
  const factor = distanceFactor(longDistance)
  return longDistance ? `Да (×${formatFactor(factor)})` : `Нет (×${formatFactor(factor)})`
}

export function requirementTooltip(
  quantity: number,
  unit: string,
  category?: string | null,
  longDistance?: boolean | null,
): string {
  const cat = (category ?? 'A').trim().toUpperCase() || 'A'
  const catF = categoryFactor(cat)
  const distF = distanceFactor(Boolean(longDistance))
  const result = calculateRequirement(quantity, cat, longDistance) ?? 0
  const distText = longDistance ? 'удалённый склад' : 'не удалённый склад'
  return `Расчёт: ${formatRequirementQty(quantity)} ${unit} × ${formatFactor(catF)} (категория ${cat}) × ${formatFactor(distF)} (${distText}) = ${formatRequirementQty(result)} ${unit}`
}
