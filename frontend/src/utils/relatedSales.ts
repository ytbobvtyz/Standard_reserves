import type { ApprovalRelatedProduct } from '../api/types'
import { formatQuantity } from './quantity'

export type RelatedSalesField =
  | 'avg_sales'
  | 'avg_sales_warehouse'
  | 'avg_sales_all_warehouses'

export function relatedProductsTooltip(
  products: ApprovalRelatedProduct[] | undefined,
  field: RelatedSalesField,
  unit: string,
): string {
  if (!products || products.length === 0) {
    return 'Нет связанных артикулов'
  }
  const lines = products.map(
    (item) => `• ${item.code} — ${item.name}: ${formatQuantity(item[field], unit)}`,
  )
  return ['Связанные артикулы:', ...lines].join('\n')
}
