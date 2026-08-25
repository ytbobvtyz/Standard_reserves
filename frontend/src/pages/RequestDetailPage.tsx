import {
  Button,
  Card,
  DatePicker,
  Descriptions,
  Modal,
  Popconfirm,
  Space,
  Table,
  Tabs,
  Timeline,
  Tooltip,
  Typography,
  message,
} from 'antd'
import type { Dayjs } from 'dayjs'
import dayjs from 'dayjs'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getApiErrorMessage } from '../api/client'
import { requestsApi } from '../api/requests'
import type {
  RequestDetail,
  RequestHistoryEntry,
  RequestItemHistoryEntry,
} from '../api/types'
import { StatusBadge } from '../components/common/StatusBadge'
import { useAuthStore } from '../stores/auth'
import {
  ACTIVE_EXPIRY_HINT,
  EXPIRY_HINT,
  expiryDecreaseError,
  maxExpiryDate,
  minExpiryDate,
} from '../utils/expiryDate'
import { formatDateTime, formatInitiator } from '../utils/format'
import {
  categoryLabel,
  distanceLabel,
  formatRequirementQty,
  requirementTooltip,
} from '../utils/requirement'
import { canDeleteByStatus, DELETE_CONFIRM } from '../utils/requestActions'

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
  executed: 'Исполнен',
}

const FIELD_LABEL: Record<string, string> = {
  quantity_requested: 'Запрошенное количество',
  quantity_approved: 'Утвержденное количество',
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
  const [itemHistory, setItemHistory] = useState<RequestItemHistoryEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [expiryModalOpen, setExpiryModalOpen] = useState(false)
  const [expiryDraft, setExpiryDraft] = useState<Dayjs | null>(null)
  const [savingExpiry, setSavingExpiry] = useState(false)

  const load = useCallback(async () => {
    if (!id) {
      return
    }
    setLoading(true)
    try {
      const { data } = await requestsApi.get(id)
      setRequest(data.data)
      try {
        const historyResp = await requestsApi.getHistory(id)
        setItemHistory(historyResp.data.data)
      } catch {
        setItemHistory([])
      }
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
  const canDelete = Boolean(isOwner && request && canDeleteByStatus(request.status))
  const canChangeActiveExpiry =
    request?.request_type === 'normative' &&
    request.status === 'active' &&
    user?.role !== 'guest'
  const canEditExpiry =
    request?.request_type === 'normative' &&
    ((user?.role === 'pp' && request?.status === 'pp_approved') ||
      (user?.role === 'economist' && request?.status === 'economy_check'))

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
      message.success('Запрос удален')
      navigate('/requests/my')
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось удалить запрос'))
    }
  }

  const openExpiryModal = () => {
    setExpiryDraft(request?.expiry_date ? dayjs(request.expiry_date) : dayjs())
    setExpiryModalOpen(true)
  }

  const saveExpiry = async () => {
    if (!id || !request || !expiryDraft) {
      return
    }
    const error = expiryDecreaseError(expiryDraft, request.expiry_date)
    if (error) {
      message.error(error)
      return
    }
    setSavingExpiry(true)
    try {
      await requestsApi.updateExpiry(id, expiryDraft.format('YYYY-MM-DD'))
      message.success('Срок действия обновлен')
      setExpiryModalOpen(false)
      await load()
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось изменить дату'))
    } finally {
      setSavingExpiry(false)
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
        <Space>
          {isOwner && isDraft ? (
            <Button type="primary" onClick={() => void submit()}>
              Отправить на согласование
            </Button>
          ) : null}
          {canChangeActiveExpiry ? (
            <Button onClick={openExpiryModal}>Изменить дату</Button>
          ) : null}
          {canDelete ? (
            <Popconfirm title={DELETE_CONFIRM} onConfirm={() => void remove()}>
              <Button danger>Удалить</Button>
            </Popconfirm>
          ) : null}
        </Space>
      </Space>
      <Card loading={loading}>
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="Тип">
            {TYPE_LABEL[request.request_type] ?? request.request_type}
          </Descriptions.Item>
          <Descriptions.Item label="Клиент">{request.client_name}</Descriptions.Item>
          <Descriptions.Item label="Инициатор">
            {formatInitiator(
              request.initiator.full_name,
              request.department_name ?? request.initiator.department,
            )}
          </Descriptions.Item>
          <Descriptions.Item label="Создан">
            {new Date(request.created_at).toLocaleString('ru-RU')}
          </Descriptions.Item>
          <Descriptions.Item label="Срок действия">
            {request.request_type === 'normative' ? (
              <Space direction="vertical" size={0}>
                <DatePicker
                  value={request.expiry_date ? dayjs(request.expiry_date) : null}
                  disabled={!canEditExpiry}
                  disabledDate={(current) =>
                    Boolean(
                      current &&
                        (current.isBefore(minExpiryDate(request.created_at), 'day') ||
                          current.isAfter(maxExpiryDate(request.created_at), 'day')),
                    )
                  }
                  format="DD.MM.YYYY"
                />
                <Typography.Text type="secondary">{EXPIRY_HINT}</Typography.Text>
                {canEditExpiry ? (
                  <Typography.Text type="secondary">
                    Изменить срок можно в окне согласования
                  </Typography.Text>
                ) : null}
              </Space>
            ) : (
              '—'
            )}
          </Descriptions.Item>
          <Descriptions.Item label="Комментарий">
            {request.initiator_comment || '—'}
          </Descriptions.Item>
          {request.request_type === 'one_time' ? (
            <>
              <Descriptions.Item label="Номер разнарядки">
                {request.order_number || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Комментарий логиста">
                {request.executed_comment || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Дата исполнения">
                {formatDateTime(request.executed_at)}
              </Descriptions.Item>
            </>
          ) : null}
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
            { title: 'Количество', dataIndex: 'quantity_requested', width: 110 },
            {
              title: 'Утверждено',
              dataIndex: 'quantity_approved',
              width: 160,
              render: (value: number | null) =>
                value == null ? '—' : `Утверждено: ${value}`,
            },
            { title: 'Ед.', dataIndex: 'unit', width: 70 },
            {
              title: 'Категория',
              width: 110,
              render: (_, item) => categoryLabel(item.product.category),
            },
            {
              title: 'Удалённость',
              width: 120,
              render: (_, item) =>
                distanceLabel(item.long_distance ?? item.warehouse.long_distance),
            },
            {
              title: 'Потребность',
              width: 140,
              render: (_, item) => {
                const qty = item.quantity_approved ?? item.quantity_requested
                const longDistance = item.long_distance ?? item.warehouse.long_distance
                const value = item.requirement
                return (
                  <Tooltip
                    title={requirementTooltip(qty, item.unit, item.product.category, longDistance)}
                  >
                    <span>
                      {formatRequirementQty(value ?? qty)} {item.unit}
                    </span>
                  </Tooltip>
                )
              },
            },
          ]}
        />
      </Card>
      <Tabs
        items={[
          {
            key: 'approval-history',
            label: 'История согласования',
            children: (
              <Timeline
                items={(request.history ?? []).map((entry) => ({
                  children: (
                    <Space direction="vertical" size={0}>
                      <Typography.Text>
                        {new Date(entry.timestamp).toLocaleString('ru-RU')} —{' '}
                        {historyTitle(entry)}
                      </Typography.Text>
                      {entry.comment ? (
                        <Typography.Text type="secondary">{entry.comment}</Typography.Text>
                      ) : null}
                    </Space>
                  ),
                }))}
              />
            ),
          },
          {
            key: 'item-history',
            label: 'История изменений',
            children: (
              <Table
                rowKey={(row) => `${row.item_id}-${row.changed_at}`}
                pagination={false}
                dataSource={itemHistory}
                locale={{ emptyText: 'Изменений позиций нет' }}
                columns={[
                  {
                    title: 'Поле',
                    dataIndex: 'field_name',
                    render: (value: string) => FIELD_LABEL[value] ?? value,
                  },
                  {
                    title: 'Было',
                    dataIndex: 'old_value',
                    width: 120,
                    render: (value: number | null) => (value == null ? '—' : value),
                  },
                  {
                    title: 'Стало',
                    dataIndex: 'new_value',
                    width: 120,
                    render: (value: number | null) => (value == null ? '—' : value),
                  },
                  {
                    title: 'Кто изменил',
                    dataIndex: ['changed_by', 'full_name'],
                  },
                  {
                    title: 'Когда',
                    dataIndex: 'changed_at',
                    render: (value: string) =>
                      new Date(value).toLocaleString('ru-RU'),
                  },
                  {
                    title: 'Комментарий',
                    dataIndex: 'comment',
                    render: (value: string | null) => value || '—',
                  },
                ]}
              />
            ),
          },
        ]}
      />
      <Modal
        title="Изменить дату"
        open={expiryModalOpen}
        onCancel={() => setExpiryModalOpen(false)}
        onOk={() => void saveExpiry()}
        okText="Сохранить"
        confirmLoading={savingExpiry}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <DatePicker
            style={{ width: '100%' }}
            value={expiryDraft}
            disabledDate={(current) =>
              Boolean(
                current &&
                  (current.isBefore(dayjs(), 'day') ||
                    (request.expiry_date &&
                      current.isAfter(dayjs(request.expiry_date), 'day'))),
              )
            }
            format="DD.MM.YYYY"
            onChange={(value) => setExpiryDraft(value)}
          />
          <Typography.Text type="secondary">{ACTIVE_EXPIRY_HINT}</Typography.Text>
        </Space>
      </Modal>
    </Space>
  )
}
