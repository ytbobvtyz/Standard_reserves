import type { ClientCoverageRow } from '../../api/types'

export interface ClientSortRow {
  label: string
  normative_tons: number
  coverage_months: number | null
  outside_normative: boolean
}

export function compareClientCoverage(left: ClientSortRow, right: ClientSortRow): number {
  const group = (row: ClientSortRow) => {
    if (row.outside_normative) {
      return 0
    }
    if (row.coverage_months == null) {
      return 1
    }
    return 2
  }
  const byGroup = group(left) - group(right)
  if (byGroup !== 0) {
    return byGroup
  }
  if (group(left) === 1 && left.normative_tons !== right.normative_tons) {
    return right.normative_tons - left.normative_tons
  }
  if (
    left.coverage_months != null &&
    right.coverage_months != null &&
    left.coverage_months !== right.coverage_months
  ) {
    return right.coverage_months - left.coverage_months
  }
  return left.label.localeCompare(right.label, 'ru')
}

export function sortClientRows<T extends ClientCoverageRow & { label: string }>(rows: T[]): T[] {
  return [...rows].sort(compareClientCoverage)
}

export function toggleCode(
  current: number[] | null,
  all: number[],
  code: number,
  checked: boolean,
): number[] | null {
  const selected = new Set(current ?? all)
  if (checked) {
    selected.add(code)
  } else {
    selected.delete(code)
  }
  if (selected.size === all.length) {
    return null
  }
  return all.filter((item) => selected.has(item))
}

export function chartBlocked(
  warehouseTotal: number,
  selectedWarehouses: number[] | null,
  productTotal: number,
  selectedProducts: number[] | null,
): boolean {
  const warehousesOff =
    warehouseTotal > 0 && selectedWarehouses !== null && selectedWarehouses.length === 0
  const productsOff =
    productTotal > 0 && selectedProducts !== null && selectedProducts.length === 0
  return warehousesOff || productsOff
}

export function clientChartHasData(
  normative: Array<number | null>,
  actual: Array<number | null>,
): boolean {
  return normative.some((value) => value != null) || actual.some((value) => value != null)
}
