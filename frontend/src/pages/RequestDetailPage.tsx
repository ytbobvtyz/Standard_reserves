import {
  Button,
  Card,
  Descriptions,
  Popconfirm,
  Space,
  Table,
  Timeline,
  Typography,
  message,
} from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getApiErrorMessage } from '../api/client'
import { requestsApi } from '../api/requests'
import type { RequestDetail, RequestHistoryEntry } from '../api/types'
import { StatusBadge } from '../components/common/StatusBadge'
import { useAuthStore } from '../stores/auth'

const TYPE_LABEL: Record<string, string> = {
  normative: 'Нормативный запас',
  one_time: 'Разовое перемещение',
}

const HISTORY_LABEL: Record<string, string> = {
  created: 'Создан',
  submitted: 'Отправлен на согласование',
  approve: 'Утвержден',
  reject: 'Отклонен',
  edit: 'Отредактирован',
  pp_reviewed: 'Рассмотрен ПП',
  economy_reviewed: 'Рассмотрен экономистом',
}

function historyTitle(entry: RequestHistoryEntry): string {
  const action = HISTORY_LABEL[entry.action] ?? entry.action
  return entry.user_name ? `${action} (${entry.user_name})` : action
}

export function RequestDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const [request, setRequest] = useState<RequestDetail | null>(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    if (!id) {
      return
    }
    setLoading(true)
    try {
      const { data } = await requestsApi.get(id)
      setRequest(data.data)
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось загрузить запрос'))
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    void load()
  }, [load])

  const isOwner = Boolean(request && user && request.initiator.id === user.id)
  const isDraft = request?.status === 'draft'

  const submit = async () => {
    if (!id) {
      return
    }
    try {
      await requestsApi.submit(id)
      message.success('Запрос отправлен на согласование')
      await load()
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось отправить запрос'))
    }
  }

  const remove = async () => {
    if (!id) {
      return
    }
    try {
      await requestsApi.remove(id)
      message.success('Черновик удален')
      navigate('/requests/my')
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось удалить запрос'))
    }
  }

  if (!request) {
    return (
      <Typography.Text type="secondary">
        {loading ? 'Загрузка...' : 'Запрос не найден'}
      </Typography.Text>
    )
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Space style={{ justifyContent: 'space-between', width: '100%' }} wrap>
        <Space>
          <Typography.Title level={3} style={{ margin: 0 }}>
            Запрос {request.id.slice(0, 8)}
          </Typography.Title>
          <StatusBadge status={request.status} />
        </Space>
        {isOwner && isDraft ? (
          <Space>
            <Button type="primary" onClick={() => void submit()}>
              Отправить на согласование
            </Button>
            <Popconfirm title="Удалить черновик?" onConfirm={() => void remove()}>
              <Button danger>Удалить</Button>
            </Popconfirm>
          </Space>
        ) : null}
      </Space>
      <Card loading={loading}>
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="Тип">
            {TYPE_LABEL[request.request_type] ?? request.request_type}
          </Descriptions.Item>
          <Descriptions.Item label="Клиент">{request.client_name}</Descriptions.Item>
          <Descriptions.Item label="Инициатор">
            {request.initiator.full_name}
            {request.initiator.department ? ` (${request.initiator.department})` : ''}
          </Descriptions.Item>
          <Descriptions.Item label="Создан">
            {new Date(request.created_at).toLocaleString('ru-RU')}
          </Descriptions.Item>
          <Descriptions.Item label="Срок действия">
            {request.expiry_date
              ? new Date(request.expiry_date).toLocaleDateString('ru-RU')
              : '—'}
          </Descriptions.Item>
          <Descriptions.Item label="Комментарий">
            {request.initiator_comment || '—'}
          </Descriptions.Item>
        </Descriptions>
      </Card>
      <Card title="Позиции">
        <Table
          rowKey="id"
          pagination={false}
          dataSource={request.items}
          columns={[
            {
              title: 'Артикул',
              dataIndex: ['product', 'code'],
              width: 110,
            },
            { title: 'Название', dataIndex: ['product', 'name'] },
            { title: 'Склад', dataIndex: ['warehouse', 'name'] },
            { title: 'Запрос', dataIndex: 'quantity_requested', width: 110 },
            {
              title: 'Утверждено',
              dataIndex: 'quantity_approved',
              width: 130,
              render: (value: number | null) => value ?? '—',
            },
            { title: 'Ед.', dataIndex: 'unit', width: 70 },
          ]}
        />
      </Card>
      <Card title="История">
        <Timeline
          items={(request.history ?? []).map((entry) => ({
            children: (
              <Space direction="vertical" size={0}>
                <Typography.Text>
                  {new Date(entry.timestamp).toLocaleString('ru-RU')} — {historyTitle(entry)}
                </Typography.Text>
                {entry.comment ? (
                  <Typography.Text type="secondary">{entry.comment}</Typography.Text>
                ) : null}
              </Space>
            ),
          }))}
        />
      </Card>
    </Space>
  )
}
