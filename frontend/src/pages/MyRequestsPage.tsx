import { Button, Input, Pagination, Select, Space, Typography, message } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { requestsApi } from '../api/requests'
import { getApiErrorMessage } from '../api/client'
import type { RequestListItem, RequestStatus, RequestType } from '../api/types'
import { RequestCard } from '../components/requests/RequestCard'
import { useAuthStore } from '../stores/auth'

const STATUS_OPTIONS: Array<{ value: RequestStatus; label: string }> = [
  { value: 'draft', label: 'Черновик' },
  { value: 'pp_approved', label: 'Ожидает ПП' },
  { value: 'economy_check', label: 'Ожидает экономиста' },
  { value: 'active', label: 'Активен' },
  { value: 'approved', label: 'Согласован' },
  { value: 'rejected', label: 'Отклонен' },
  { value: 'executed', label: 'Исполнен' },
]

export function MyRequestsPage() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const canCreate = user?.role === 'commercial' || user?.role === 'logistics'
  const title =
    user?.role === 'pp' || user?.role === 'economist' || user?.role === 'logistics'
      ? 'Запросы'
      : 'Мои запросы'

  const [items, setItems] = useState<RequestListItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<RequestStatus | undefined>()
  const [type, setType] = useState<RequestType | undefined>()
  const [clientName, setClientName] = useState('')
  const [page, setPage] = useState(1)
  const limit = 10

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await requestsApi.list({
        status,
        type,
        client_name: clientName || undefined,
        page,
        limit,
      })
      setItems(data.data)
      setTotal(data.meta?.total ?? data.data.length)
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось загрузить запросы'))
    } finally {
      setLoading(false)
    }
  }, [status, type, clientName, page])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Space style={{ justifyContent: 'space-between', width: '100%' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>
          {title}
        </Typography.Title>
        {canCreate ? (
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/requests/create')}
          >
            Создать запрос
          </Button>
        ) : null}
      </Space>
      <Space wrap>
        <Select
          allowClear
          placeholder="Статус"
          style={{ width: 200 }}
          value={status}
          onChange={(value) => {
            setPage(1)
            setStatus(value)
          }}
          options={STATUS_OPTIONS}
        />
        <Select
          allowClear
          placeholder="Тип"
          style={{ width: 180 }}
          value={type}
          onChange={(value) => {
            setPage(1)
            setType(value)
          }}
          options={[
            { value: 'normative', label: 'Норматив' },
            { value: 'one_time', label: 'Разовое' },
          ]}
        />
        <Input.Search
          allowClear
          placeholder="Клиент"
          style={{ width: 240 }}
          onSearch={(value) => {
            setPage(1)
            setClientName(value)
          }}
        />
      </Space>
      {loading ? <Typography.Text type="secondary">Загрузка...</Typography.Text> : null}
      {!loading && items.length === 0 ? (
        <Typography.Text type="secondary">Запросы не найдены</Typography.Text>
      ) : null}
      {items.map((item) => (
        <RequestCard key={item.id} request={item} />
      ))}
      <Pagination
        current={page}
        pageSize={limit}
        total={total}
        onChange={setPage}
        hideOnSinglePage
      />
    </Space>
  )
}
