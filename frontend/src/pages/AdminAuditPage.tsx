import {
  Button,
  DatePicker,
  Input,
  Select,
  Space,
  Table,
  Typography,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { Dayjs } from 'dayjs'
import dayjs from 'dayjs'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminApi } from '../api/admin'
import { getApiErrorMessage } from '../api/client'
import type { AdminUser, AuditEvent } from '../api/types'
import { ROLE_LABEL } from '../components/admin/roles'

const { RangePicker } = DatePicker

type Preset = 'today' | 'week' | 'month' | 'all' | 'custom'

const EVENT_TYPE_LABEL: Record<string, string> = {
  user_logged_in: 'Вход на портал',
  user_registered: 'Регистрация пользователя',
  user_updated: 'Изменение пользователя',
  user_deleted: 'Удаление пользователя',
  password_changed: 'Смена пароля',
  product_created: 'Создание продукта',
  product_updated: 'Изменение продукта',
  product_deleted: 'Удаление продукта',
  client_created: 'Создание клиента',
  client_updated: 'Изменение клиента',
  client_deleted: 'Удаление клиента',
  object_created: 'Создание объекта',
  object_updated: 'Изменение объекта',
  object_deleted: 'Удаление объекта',
  request_created: 'Создание запроса',
  request_submitted: 'Отправка запроса',
  request_approved: 'Согласование запроса',
  request_rejected: 'Отклонение запроса',
  request_deleted: 'Удаление запроса',
  request_expiry_changed: 'Изменение даты норматива',
  balances_uploaded: 'Загрузка остатков',
  actual_shipments_uploaded: 'Загрузка реализации',
  production_request_uploaded: 'Загрузка партии нормативов',
  export_generated: 'Экспорт Excel',
  normative_active: 'Норматив активирован',
  normative_expired: 'Норматив истёк',
  deficit_detected: 'Обнаружен дефицит',
  deficit_resolved: 'Дефицит закрыт',
  normative_replaced_by_name: 'Норматив заменён по имени',
}

const EVENT_OPTIONS = Object.entries(EVENT_TYPE_LABEL).map(([value, label]) => ({
  value,
  label,
}))

const ALL_TIME_FROM = '2020-01-01'

function startOfWeek(value: Dayjs): Dayjs {
  const day = value.day()
  const diff = day === 0 ? 6 : day - 1
  return value.subtract(diff, 'day').startOf('day')
}

function rangeFor(preset: Exclude<Preset, 'custom'>): [Dayjs, Dayjs] {
  const today = dayjs().endOf('day')
  if (preset === 'today') {
    return [dayjs().startOf('day'), today]
  }
  if (preset === 'week') {
    return [startOfWeek(dayjs()), today]
  }
  if (preset === 'month') {
    return [dayjs().startOf('month'), today]
  }
  return [dayjs(ALL_TIME_FROM).startOf('day'), today]
}

function entityText(row: AuditEvent): string {
  const label = row.entity_label || ''
  if (row.entity_type === 'request' && row.entity_id) {
    const number = `№${row.entity_id.slice(0, 8)}`
    return label ? `${number} ${label}` : number
  }
  return label || '—'
}

function entityHref(row: AuditEvent): string | null {
  if (row.entity_type === 'request' && row.entity_id) {
    return `/requests/${row.entity_id}`
  }
  if (row.entity_type === 'product' && row.details.code != null) {
    return `/references/products/${String(row.details.code)}`
  }
  return null
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString('ru-RU')
}

function formatTime(value: string): string {
  return new Date(value).toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export function AdminAuditPage() {
  const [preset, setPreset] = useState<Preset>('today')
  const [range, setRange] = useState<[Dayjs, Dayjs]>(() => rangeFor('today'))
  const [userId, setUserId] = useState<string | undefined>()
  const [eventType, setEventType] = useState<string | undefined>()
  const [requestNumber, setRequestNumber] = useState('')
  const [users, setUsers] = useState<AdminUser[]>([])
  const [items, setItems] = useState<AuditEvent[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const limit = 50

  useEffect(() => {
    let cancelled = false
    void adminApi
      .getUsers({ page: 1, limit: 200 })
      .then(({ data }) => {
        if (!cancelled) {
          setUsers(data.data)
        }
      })
      .catch(() => {
        if (!cancelled) {
          message.error('Не удалось загрузить список пользователей')
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await adminApi.getAudit({
        date_from: range[0].format('YYYY-MM-DD'),
        date_to: range[1].format('YYYY-MM-DD'),
        user_id: userId,
        event_type: eventType,
        request_number: requestNumber.trim() || undefined,
        page,
        limit,
      })
      setItems(data.data)
      setTotal(data.meta?.total ?? data.data.length)
    } catch (err) {
      message.error(getApiErrorMessage(err, 'Не удалось загрузить журнал'))
    } finally {
      setLoading(false)
    }
  }, [eventType, page, range, requestNumber, userId])

  useEffect(() => {
    void load()
  }, [load])

  const applyPreset = (next: Exclude<Preset, 'custom'>) => {
    setPreset(next)
    setRange(rangeFor(next))
    setPage(1)
  }

  const columns: ColumnsType<AuditEvent> = [
    {
      title: 'Дата',
      dataIndex: 'created_at',
      width: 120,
      render: (value: string) => formatDate(value),
    },
    {
      title: 'Время',
      dataIndex: 'created_at',
      width: 110,
      render: (value: string) => formatTime(value),
    },
    {
      title: 'Пользователь',
      key: 'user',
      render: (_value, row) => {
        if (!row.user) {
          return 'Система'
        }
        const role = ROLE_LABEL[row.user.role] ?? row.user.role
        return `${row.user.full_name} · ${role}`
      },
    },
    {
      title: 'Тип активности',
      dataIndex: 'event_type',
      render: (value: string) => EVENT_TYPE_LABEL[value] ?? value,
    },
    {
      title: 'Объект',
      key: 'entity',
      render: (_value, row) => {
        const text = entityText(row)
        const href = entityHref(row)
        if (!href) {
          return text
        }
        return <Link to={href}>{text}</Link>
      },
    },
  ]

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={3}>Журнал действий</Typography.Title>
      <Space wrap>
        <Button
          type={preset === 'today' ? 'primary' : 'default'}
          onClick={() => applyPreset('today')}
        >
          Сегодня
        </Button>
        <Button
          type={preset === 'week' ? 'primary' : 'default'}
          onClick={() => applyPreset('week')}
        >
          Неделя
        </Button>
        <Button
          type={preset === 'month' ? 'primary' : 'default'}
          onClick={() => applyPreset('month')}
        >
          Месяц
        </Button>
        <Button
          type={preset === 'all' ? 'primary' : 'default'}
          onClick={() => applyPreset('all')}
        >
          Всё время
        </Button>
        <RangePicker
          allowClear={false}
          value={range}
          format="DD.MM.YYYY"
          onChange={(values) => {
            if (!values?.[0] || !values[1]) {
              applyPreset('today')
              return
            }
            setPreset('custom')
            setPage(1)
            setRange([values[0].startOf('day'), values[1].endOf('day')])
          }}
        />
        <Select
          allowClear
          showSearch
          optionFilterProp="label"
          placeholder="Пользователь"
          style={{ width: 280 }}
          value={userId}
          options={users.map((item) => ({
            value: item.id,
            label: `${item.full_name} (${ROLE_LABEL[item.role] ?? item.role})`,
          }))}
          onChange={(value) => {
            setPage(1)
            setUserId(value)
          }}
        />
        <Input
          allowClear
          placeholder="Номер запроса"
          style={{ width: 200 }}
          value={requestNumber}
          onChange={(event) => {
            setPage(1)
            setRequestNumber(event.target.value)
          }}
        />
        <Select
          allowClear
          showSearch
          optionFilterProp="label"
          placeholder="Тип активности"
          style={{ width: 280 }}
          value={eventType}
          options={EVENT_OPTIONS}
          onChange={(value) => {
            setPage(1)
            setEventType(value)
          }}
        />
      </Space>
      <Table
        rowKey="id"
        loading={loading}
        dataSource={items}
        columns={columns}
        pagination={{
          current: page,
          pageSize: limit,
          total,
          showSizeChanger: false,
          onChange: setPage,
        }}
        expandable={{
          expandedRowRender: (row) => (
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
              {JSON.stringify(row.details ?? {}, null, 2)}
            </pre>
          ),
          rowExpandable: (row) => Object.keys(row.details ?? {}).length > 0,
        }}
      />
    </Space>
  )
}
