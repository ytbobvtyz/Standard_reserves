import {
  Button,
  Input,
  Pagination,
  Select,
  Space,
  Table,
  Typography,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { approvalsApi } from '../api/approvals'
import { getApiErrorMessage } from '../api/client'
import type {
  ApprovalActionPayload,
  ApprovalPendingItem,
  ApprovalPendingRequest,
  RequestType,
} from '../api/types'
import { ApprovalModal } from '../components/approvals/ApprovalModal'
import { StatusBadge } from '../components/common/StatusBadge'

const TYPE_LABEL: Record<RequestType, string> = {
  normative: 'Норматив',
  one_time: 'Разовое',
}

export function ApprovalsPage() {
  const location = useLocation()
  const isEconomy = location.pathname.includes('economy')
  const title = isEconomy ? 'Согласование экономиста' : 'Согласование ПП'
  const expectedStatus = isEconomy ? 'economy_check' : 'pp_approved'

  const [items, setItems] = useState<ApprovalPendingRequest[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [type, setType] = useState<RequestType | undefined>()
  const [clientName, setClientName] = useState('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<ApprovalPendingRequest | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const limit = 10

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const request = isEconomy
        ? approvalsApi.getEconomyPending
        : approvalsApi.getPPPending
      const { data } = await request({
        type,
        page,
        limit,
        client_name: clientName || undefined,
      })
      setItems(data.data)
      setTotal(data.meta?.total ?? data.data.length)
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось загрузить запросы'))
    } finally {
      setLoading(false)
    }
  }, [isEconomy, type, page, clientName])

  useEffect(() => {
    void load()
  }, [load])

  const closeModal = () => {
    setSelected(null)
  }

  const submitAction = async (payload: ApprovalActionPayload) => {
    if (!selected) {
      return
    }

    setSubmitting(true)
    try {
      const request = isEconomy ? approvalsApi.economyAction : approvalsApi.ppAction
      const { data } = await request(selected.id, payload)
      const nextStatus = data.data.status
      const statusLabel =
        nextStatus === 'rejected'
          ? 'отклонен'
          : nextStatus === 'active' || nextStatus === 'approved'
              ? 'утвержден'
              : 'согласован'
      message.success(`Запрос ${statusLabel}`)
      closeModal()
      await load()
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось выполнить действие'))
    } finally {
      setSubmitting(false)
    }
  }

  const columns: ColumnsType<ApprovalPendingRequest> = [
      {
        title: 'ID',
        dataIndex: 'id',
        width: 110,
        render: (value: string) => value.slice(0, 8),
      },
      { title: 'Клиент', dataIndex: 'client_name' },
      {
        title: 'Тип',
        dataIndex: 'request_type',
        width: 130,
        render: (value: RequestType) => TYPE_LABEL[value] ?? value,
      },
      {
        title: 'Позиции',
        dataIndex: 'items',
        width: 110,
        render: (value: ApprovalPendingItem[]) => value.length,
      },
      {
        title: 'Дата',
        dataIndex: 'created_at',
        width: 130,
        render: (value: string) => new Date(value).toLocaleDateString('ru-RU'),
      },
      {
        title: 'Статус',
        width: 180,
        render: () => <StatusBadge status={expectedStatus} />,
      },
      {
        title: '',
        width: 120,
        render: (_, record) => (
          <Button
            type="link"
            onClick={(event) => {
              event.stopPropagation()
              setSelected(record)
            }}
          >
            Открыть
          </Button>
        ),
      },
    ]

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Space style={{ justifyContent: 'space-between', width: '100%' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>
          {title}
        </Typography.Title>
        <Typography.Text type="secondary">Ожидают: {total}</Typography.Text>
      </Space>
      <Space wrap>
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
      <Table
        rowKey="id"
        loading={loading}
        columns={columns}
        dataSource={items}
        pagination={false}
        onRow={(record) => ({
          onClick: () => setSelected(record),
          style: { cursor: 'pointer' },
        })}
      />
      <Pagination
        current={page}
        pageSize={limit}
        total={total}
        onChange={setPage}
        hideOnSinglePage
      />
      <ApprovalModal
        request={selected}
        submitting={submitting}
        stage={isEconomy ? 'economy' : 'pp'}
        onCancel={closeModal}
        onSubmit={submitAction}
      />
    </Space>
  )
}
