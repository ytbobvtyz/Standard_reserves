import { Button, Card, Popconfirm, Space, Typography } from 'antd'
import { useNavigate } from 'react-router-dom'
import type { RequestListItem } from '../../api/types'
import { DELETE_CONFIRM } from '../../utils/requestActions'
import { StatusBadge } from '../common/StatusBadge'

const TYPE_LABEL: Record<string, string> = {
  normative: 'Норматив',
  one_time: 'Разовое',
}

interface RequestCardProps {
  request: RequestListItem
  canDelete?: boolean
  onDelete?: () => void
}

export function RequestCard({ request, canDelete = false, onDelete }: RequestCardProps) {
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
          {request.department_name || request.initiator.department ? (
            <Typography.Text type="secondary">
              Подразделение:{' '}
              {request.department_name ?? request.initiator.department}
            </Typography.Text>
          ) : null}
        <Space style={{ justifyContent: 'space-between', width: '100%' }}>
          <Typography.Text type="secondary">
            Инициатор: {request.initiator.full_name}
          </Typography.Text>
          {canDelete && onDelete ? (
            <Popconfirm
              title={DELETE_CONFIRM}
              onConfirm={(event) => {
                event?.stopPropagation()
                onDelete()
              }}
              onCancel={(event) => event?.stopPropagation()}
            >
              <Button
                danger
                size="small"
                onClick={(event) => event.stopPropagation()}
              >
                Удалить
              </Button>
            </Popconfirm>
          ) : null}
        </Space>
      </Space>
    </Card>
  )
}
