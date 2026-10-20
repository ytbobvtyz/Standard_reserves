import type { DashboardMassUnit } from '../../api/types'

export function formatMass(value: number, unit: DashboardMassUnit): string {
  const digits = unit === 'т' ? 6 : 3
  return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: digits }).format(value)
}

export function formatKpiMass(value: number): string {
  return new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3,
  }).format(value)
}

export const COVERAGE_WITH_TRANSFERS_HINT =
  'Покрытие с учётом перемещений = (общий НЗ − сумма дефицитов) / общий НЗ × 100%. Дефицит позиции = max(0, норматив − запланировано). Если общий НЗ равен нулю, покрытие 0%. Если все позиции покрыты, покрытие 100%.'

export const COVERAGE_AVAILABLE_HINT =
  'Покрытие доступным стоком = (общий НЗ − сумма дефицитов по доступному остатку) / общий НЗ × 100%. Дефицит позиции = max(0, норматив − доступно), без учёта плана перемещений.'
