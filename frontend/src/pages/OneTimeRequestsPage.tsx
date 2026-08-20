import {
  AutoComplete,
  Button,
  DatePicker,
  Form,
  Input,
  Modal,
  Pagination,
  Select,
  Space,
  Table,
  Tabs,
  Typography,
  message,
} from 'antd'
import { DownloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getApiErrorMessage } from '../api/client'
import { logisticsApi } from '../api/logistics'
import { referencesApi } from '../api/references'
import type {
  ObjectListItem,
  OneTimeInitiator,
  OneTimeListItem,
  RequestStatus,
} from '../api/types'
import { StatusBadge } from '../components/common/StatusBadge'

interface FilterState {
  warehouse_code?: number
  client_name?: string
  initiator_id?: string
  from_date?: string
  to_date?: string
  status?: RequestStatus
}

const STATUS_OPTIONS: Array<{ value: RequestStatus; label: string }> = [
  { value: 'approved', label: 'Согласован' },
  { value: 'executed', label: 'Исполнен' },
  { value: 'rejected', label: 'Отклонен' },
]

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString('ru-RU')
}

function formatItems(items: OneTimeListItem['items']): string {
  if (items.length === 0) {
    return '—'
  }
  if (items.length === 1) {
    const item = items[0]
    return `1 позиция: ${item.quantity} ${item.unit} ${item.product_name}`
  }
  return `${items.length} позиции: ${items
    .map((item) => `${item.quantity} ${item.unit}`)
    .join(', ')}`
}

function warehouseLabel(items: OneTimeListItem['items']): string {
  const names = [...new Set(items.map((item) => item.warehouse_name))]
  return names.join(', ') || '—'
}

export function OneTimeRequestsPage() {
  const navigate = useNavigate()
  const [draft, setDraft] = useState<FilterState>({})
  const [applied, setApplied] = useState<FilterState>({})
  const [items, setItems] = useState<OneTimeListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [warehouses, setWarehouses] = useState<ObjectListItem[]>([])
  const [initiators, setInitiators] = useState<OneTimeInitiator[]>([])
  const [clients, setClients] = useState<string[]>([])
  const [selected, setSelected] = useState<OneTimeListItem | null>(null)
  const [orderNumber, setOrderNumber] = useState('')
  const [comment, setComment] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [exportingId, setExportingId] = useState<string | null>(null)
  const limit = 10

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await logisticsApi.getOneTimeList({
        ...applied,
        page,
        limit,
      })
      setItems(data.data)
      setTotal(data.meta?.total ?? data.data.length)
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось загрузить разовые запросы'))
    } finally {
      setLoading(false)
    }
  }, [applied, page])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    void Promise.all([
      referencesApi.getObjects({ type: 'warehouse', is_active: true, limit: 100 }),
      logisticsApi.getInitiators(),
      logisticsApi.getClients(),
    ])
      .then(([objectsResp, initiatorsResp, clientsResp]) => {
        setWarehouses(objectsResp.data.data)
        setInitiators(initiatorsResp.data.data)
        setClients(clientsResp.data.data)
      })
      .catch((error) => {
        message.error(getApiErrorMessage(error, 'Не удалось загрузить фильтры'))
      })
  }, [])

  const applyFilters = () => {
    setPage(1)
    setApplied({ ...draft })
  }

  const resetFilters = () => {
    setDraft({})
    setApplied({})
    setPage(1)
  }

  const openExecute = (request: OneTimeListItem) => {
    setSelected(request)
    setOrderNumber('')
    setComment('')
  }

  const closeExecute = () => {
    setSelected(null)
    setOrderNumber('')
    setComment('')
  }

  const confirmExecute = async () => {
    if (!selected) {
      return
    }
    if (!orderNumber.trim()) {
      message.error('Номер разнарядки обязателен')
      return
    }
    setSubmitting(true)
    try {
      await logisticsApi.executeOneTime(selected.id, {
        order_number: orderNumber.trim(),
        comment: comment.trim() || undefined,
      })
      message.success('Запрос отмечен как исполненный')
      closeExecute()
      await load()
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось исполнить запрос'))
    } finally {
      setSubmitting(false)
    }
  }

  const handleExport = async (requestId: string) => {
    setExportingId(requestId)
    try {
      const { data } = await logisticsApi.exportOneTime(requestId)
      downloadBlob(data, `one-time-${requestId}.xlsx`)
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось выгрузить Excel'))
    } finally {
      setExportingId(null)
    }
  }

  const clientOptions = useMemo(
    () => clients.map((name) => ({ value: name })),
    [clients],
  )

  const columns: ColumnsType<OneTimeListItem> = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 120,
      render: (value: string) => value.slice(0, 8),
    },
    { title: 'Клиент', dataIndex: 'client_name' },
    {
      title: 'Склад',
      key: 'warehouse',
      render: (_, record) => warehouseLabel(record.items),
    },
    {
      title: 'Заявитель',
      dataIndex: ['initiator', 'full_name'],
    },
    {
      title: 'Дата',
      dataIndex: 'created_at',
      width: 120,
      render: (value: string) => formatDate(value),
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      width: 140,
      render: (value: RequestStatus) => <StatusBadge status={value} />,
    },
    {
      title: 'Позиции',
      key: 'items',
      render: (_, record) => formatItems(record.items),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 260,
      render: (_, record) => (
        <Space>
          {record.status === 'approved' ? (
            <Button type="primary" size="small" onClick={() => openExecute(record)}>
              Исполнить
            </Button>
          ) : null}
          <Button
            size="small"
            icon={<DownloadOutlined />}
            loading={exportingId === record.id}
            onClick={() => void handleExport(record.id)}
          >
            Скачать Excel
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Tabs
        activeKey="one-time"
        onChange={(key) => {
          if (key === 'normative') {
            navigate('/logistics/dashboard')
          }
        }}
        items={[
          { key: 'normative', label: 'Нормативы' },
          { key: 'one-time', label: 'Разовые перемещения' },
        ]}
      />
      <Typography.Title level={3} style={{ margin: 0 }}>
        Разовые перемещения
      </Typography.Title>
      <Space wrap>
        <Select
          allowClear
          aria-label="Склад"
          placeholder="Склад"
          style={{ width: 220 }}
          value={draft.warehouse_code}
          onChange={(value) =>
            setDraft((current) => ({ ...current, warehouse_code: value }))
          }
          options={warehouses.map((item) => ({
            value: item.code,
            label: `${item.code} · ${item.name}`,
          }))}
        />
        <AutoComplete
          aria-label="Клиент"
          style={{ width: 240 }}
          options={clientOptions}
          value={draft.client_name}
          onChange={(value) =>
            setDraft((current) => ({ ...current, client_name: value || undefined }))
          }
          filterOption={(input, option) =>
            String(option?.value ?? '')
              .toLowerCase()
              .includes(input.toLowerCase())
          }
        >
          <Input aria-label="Клиент" placeholder="Клиент" allowClear />
        </AutoComplete>
        <Select
          allowClear
          aria-label="Заявитель"
          placeholder="Заявитель"
          style={{ width: 240 }}
          value={draft.initiator_id}
          onChange={(value) =>
            setDraft((current) => ({ ...current, initiator_id: value }))
          }
          options={initiators.map((item) => ({
            value: item.id,
            label: item.full_name,
          }))}
        />
        <DatePicker
          placeholder="Дата с"
          onChange={(_value, dateString) =>
            setDraft((current) => ({
              ...current,
              from_date: (dateString as string) || undefined,
            }))
          }
        />
        <DatePicker
          placeholder="Дата по"
          onChange={(_value, dateString) =>
            setDraft((current) => ({
              ...current,
              to_date: (dateString as string) || undefined,
            }))
          }
        />
        <Select
          allowClear
          aria-label="Статус"
          placeholder="Статус"
          style={{ width: 180 }}
          value={draft.status}
          onChange={(value) => setDraft((current) => ({ ...current, status: value }))}
          options={STATUS_OPTIONS}
        />
        <Button type="primary" onClick={applyFilters}>
          Применить фильтр
        </Button>
        <Button onClick={resetFilters}>Сбросить</Button>
      </Space>
      <Table
        rowKey="id"
        loading={loading}
        pagination={false}
        columns={columns}
        dataSource={items}
        onRow={(record) => ({
          onClick: (event) => {
            const target = event.target as HTMLElement
            if (target.closest('button')) {
              return
            }
            navigate(`/requests/${record.id}`)
          },
        })}
      />
      <Pagination
        current={page}
        pageSize={limit}
        total={total}
        onChange={setPage}
        showSizeChanger={false}
      />
      <Modal
        title={selected ? `Исполнить запрос №${selected.id.slice(0, 8)}` : 'Исполнить'}
        open={Boolean(selected)}
        onCancel={closeExecute}
        footer={
          <Space>
            <Button onClick={closeExecute}>Отмена</Button>
            <Button type="primary" loading={submitting} onClick={() => void confirmExecute()}>
              Подтвердить
            </Button>
          </Space>
        }
      >
        <Form layout="vertical">
          <Form.Item label="Номер разнарядки" required>
            <Input
              value={orderNumber}
              onChange={(event) => setOrderNumber(event.target.value)}
              placeholder="РН-2026-08-20-001"
            />
          </Form.Item>
          <Form.Item label="Комментарий">
            <Input.TextArea
              value={comment}
              onChange={(event) => setComment(event.target.value)}
              rows={3}
              placeholder="Отгрузка произведена"
            />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  )
}
