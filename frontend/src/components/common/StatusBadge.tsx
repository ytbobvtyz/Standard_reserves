import { Tag } from 'antd'
import type { RequestStatus } from '../../api/types'

const STATUS_MAP: Record<RequestStatus, { color: string; label: string }> = {
  draft: { color: 'default', label: 'Черновик' },
  pp_approved: { color: 'blue', label: 'Ожидает ПП' },
  economy_check: { color: 'processing', label: 'Ожидает экономиста' },
  pp_rework: { color: 'gold', label: 'Доработка ПП' },
  economy_rework: { color: 'gold', label: 'Доработка экономиста' },
  active: { color: 'green', label: 'Активен' },
  approved: { color: 'green', label: 'Согласован' },
  rejected: { color: 'red', label: 'Отклонен' },
  expired: { color: 'default', label: 'Истек' },
  executed: { color: 'cyan', label: 'Исполнен' },
}

export function StatusBadge({ status }: { status: RequestStatus | string }) {
  const item = STATUS_MAP[status as RequestStatus] ?? {
    color: 'default',
    label: status,
  }
  return <Tag color={item.color}>{item.label}</Tag>
}
