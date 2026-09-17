import type { DashboardMassUnit } from '../../api/types'

export function formatMass(value: number, unit: DashboardMassUnit): string {
  const digits = unit === 'т' ? 6 : 3
  return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: digits }).format(value)
}

export const COVERAGE_HINT =
  'Покрытие — доля потребности в нормативе запаса, которую закрывает текущий план (остатки и план отгрузки). Считается как план ÷ потребность × 100% и не превышает 100%. Потребность берётся из количества НЗ с учётом категории клиента и коэффициента дальних перевозок.'
