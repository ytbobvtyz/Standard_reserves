import type { RelatedProduct } from '../../api/types'

export interface MaterialHistoryItem {
  code: number
  name: string
  isActive: boolean
  kind: 'current' | 'parent' | 'child'
}

export function orderedMaterials(
  current: { code: number; name: string; isActive: boolean },
  related: RelatedProduct[],
): MaterialHistoryItem[] {
  const byCode = (left: RelatedProduct, right: RelatedProduct) => left.code - right.code
  const parents = related.filter((item) => item.relation === 'parent').sort(byCode)
  const children = related.filter((item) => item.relation === 'child').sort(byCode)
  const row = (item: RelatedProduct, kind: 'parent' | 'child'): MaterialHistoryItem => ({
    code: item.code,
    name: item.name,
    isActive: item.is_active,
    kind,
  })
  return [
    ...parents.map((item) => row(item, 'parent')),
    {
      code: current.code,
      name: current.name,
      isActive: current.isActive,
      kind: 'current',
    },
    ...children.map((item) => row(item, 'child')),
  ]
}
