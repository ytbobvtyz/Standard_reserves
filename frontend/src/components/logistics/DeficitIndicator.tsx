import { Tag } from 'antd'
import type { DeficitStatus } from '../../api/types'

interface DeficitIndicatorProps {
  deficit: number
  status?: DeficitStatus
  unit?: string
}

function formatDeficit(value: number): string {
  return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 4 }).format(value)
}

export function DeficitIndicator({
  deficit,
  status,
  unit,
}: DeficitIndicatorProps) {
  const resolved = status ?? (deficit > 0 ? 'warning' : 'ok')
  const color = resolved === 'warning' ? 'red' : 'green'
  const suffix = unit ? ` ${unit}` : ''
  return (
    <Tag color={color}>
      {formatDeficit(deficit)}
      {suffix}
    </Tag>
  )
}
