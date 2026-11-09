export interface CoverageThresholds {
  highMonths: number
  lowMonths: number
}

export const DEFAULT_COVERAGE_THRESHOLDS: CoverageThresholds = {
  highMonths: 2,
  lowMonths: 4,
}

export type CoverageLevel = 'high' | 'normal' | 'low' | 'none'

export function stockAfterApproval(input: {
  requestType: string
  autoComplete: boolean
  quantity: number
  existingNz: number | null
}): number {
  if (input.requestType !== 'normative' || input.autoComplete) {
    return input.quantity
  }
  return (input.existingNz ?? 0) + input.quantity
}

export function coverageMonths(
  stock: number,
  monthlySales: number | null | undefined,
): number | null {
  if (monthlySales == null || monthlySales <= 0) {
    return null
  }
  return stock / monthlySales
}

export function coverageLevel(
  months: number | null,
  thresholds: CoverageThresholds,
): CoverageLevel {
  if (months == null) {
    return 'none'
  }
  if (months <= thresholds.highMonths) {
    return 'high'
  }
  if (months <= thresholds.lowMonths) {
    return 'normal'
  }
  return 'low'
}

export function needsReview(
  months: number | null,
  thresholds: CoverageThresholds,
): boolean {
  const level = coverageLevel(months, thresholds)
  return level === 'low' || level === 'none'
}

export function formatCoverage(months: number | null): string {
  if (months == null) {
    return 'нет реализации'
  }
  const rounded = Math.round(months * 10) / 10
  return `${rounded.toFixed(1).replace('.', ',')} мес`
}

export function coverageSummary(reviewCount: number, total: number): string {
  if (total === 0 || reviewCount === 0) {
    return 'Позиции не требуют разбора'
  }
  return `${reviewCount} из ${total} позиций требуют разбора`
}

export function compareCoverageRows(
  left: number | null,
  right: number | null,
  thresholds: CoverageThresholds,
): number {
  const rank = (months: number | null) => {
    if (months == null) {
      return 0
    }
    if (months > thresholds.lowMonths) {
      return 1
    }
    return 2
  }
  const byRank = rank(left) - rank(right)
  if (byRank !== 0) {
    return byRank
  }
  if (left == null || right == null) {
    return 0
  }
  return right - left
}

export function coverageContext(input: {
  stock: number
  monthlySales: number | null
  warehouseMonthlySales: number | null
  productMonthlySales: number | null
  thresholds: CoverageThresholds
}): string | null {
  const client = coverageMonths(input.stock, input.monthlySales)
  if (!needsReview(client, input.thresholds)) {
    return null
  }
  const warehouse = coverageMonths(input.stock, input.warehouseMonthlySales)
  const product = coverageMonths(input.stock, input.productMonthlySales)
  const { highMonths, lowMonths } = input.thresholds
  if (client == null) {
    if (warehouse != null && warehouse <= highMonths) {
      return 'У клиента нет реализации. На складе артикул уходит быстрее.'
    }
    if (product == null || product > lowMonths) {
      return 'Реализации нет и по другим складам.'
    }
    return null
  }
  if (product == null || product > lowMonths) {
    return 'Артикул медленный на всех складах.'
  }
  if (warehouse != null && warehouse <= highMonths) {
    return 'На складе артикул уходит быстрее. Медленный только этот клиент.'
  }
  return null
}
