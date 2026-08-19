import { Card, Space, Typography } from 'antd'
import { useNavigate } from 'react-router-dom'
import type { RequestListItem } from '../../api/types'
import { StatusBadge } from '../common/StatusBadge'

const TYPE_LABEL: Record<string, string> = {
  normative: 'Норматив',
  one_time: 'Разовое',
}

export function RequestCard({ request }: { request: RequestListItem }) {
  const navigate = useNavigate()

  return (
    <Card
      hoverable
      size="small"
      onClick={() => navigate(`/requests/${request.id}`)}
      style={{ marginBottom: 12 }}
    >
      <Space direction="vertical" size={4} style={{ width: '100%' }}>
        <Space style={{ justifyContent: 'space-between', width: '100%' }}>
          <Typography.Text strong>{request.client_name}</Typography.Text>
          <StatusBadge status={request.status} />
        </Space>
        <Typography.Text type="secondary">
          {TYPE_LABEL[request.request_type] ?? request.request_type} ·{' '}
          {request.items_count}{' '}
          {request.items_count === 1 ? 'позиция' : 'позиций'} ·{' '}
          {new Date(request.created_at).toLocaleDateString('ru-RU')}
        </Typography.Text>
        <Typography.Text type="secondary">
          Инициатор: {request.initiator.full_name}
        </Typography.Text>
      </Space>
    </Card>
  )
}
