import {
  Button,
  Input,
  InputNumber,
  Modal,
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
  ApprovalAction,
  ApprovalPendingItem,
  ApprovalPendingRequest,
  RequestType,
} from '../api/types'
import { StatusBadge } from '../components/common/StatusBadge'

const TYPE_LABEL: Record<RequestType, string> = {
  normative: 'Норматив',
  one_time: 'Разовое',
}

interface EditableItem extends ApprovalPendingItem {
  quantity_approved_input: number
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
  const [editableItems, setEditableItems] = useState<EditableItem[]>([])
  const [comment, setComment] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const limit = 10

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const request = isEconomy
        ? approvalsApi.getEconomyPending
        : approvalsApi.getPPPending
      const { data } = await request({ type, page, limit })
      const filtered = clientName
        ? data.data.filter((item) =>
            item.client_name.toLowerCase().includes(clientName.toLowerCase()),
          )
        : data.data
      setItems(filtered)
      setTotal(clientName ? filtered.length : (data.meta?.total ?? data.data.length))
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось загрузить запросы'))
    } finally {
      setLoading(false)
    }
  }, [isEconomy, type, page, clientName])

  useEffect(() => {
    void load()
  }, [load])

  const openModal = (request: ApprovalPendingRequest) => {
    setSelected(request)
    setComment('')
    setEditableItems(
      request.items.map((item) => ({
        ...item,
        quantity_approved_input: item.quantity_approved ?? item.quantity_requested,
      })),
    )
  }

  const closeModal = () => {
    setSelected(null)
    setEditableItems([])
    setComment('')
  }

  const submitAction = async (action: ApprovalAction) => {
    if (!selected) {
      return
    }
    if (action === 'reject' && !comment.trim()) {
      message.error('Комментарий обязателен при отказе')
      return
    }
    if (action === 'edit') {
      const invalid = editableItems.some((item) => item.quantity_approved_input <= 0)
      if (invalid) {
        message.error('Утвержденное количество должно быть больше 0')
        return
      }
    }

    setSubmitting(true)
    try {
      const payload =
        action === 'edit'
          ? {
              action,
              comment: comment.trim() || undefined,
              items: editableItems.map((item) => ({
                product_code: item.product_code,
                warehouse_code: item.warehouse_code,
                quantity_approved: item.quantity_approved_input,
              })),
            }
          : { action, comment: comment.trim() || undefined }

      const request = isEconomy ? approvalsApi.economyAction : approvalsApi.ppAction
      const { data } = await request(selected.id, payload)
      const nextStatus = data.data.status
      const statusLabel =
        nextStatus === 'rejected'
          ? 'отклонен'
          : nextStatus === 'economy_rework'
            ? 'отправлен на доработку'
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
              openModal(record)
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
          onClick: () => openModal(record),
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
      <Modal
        title={
          selected
            ? `Согласование запроса №${selected.id.slice(0, 8)}`
            : 'Согласование запроса'
        }
        open={Boolean(selected)}
        onCancel={closeModal}
        width={860}
        footer={
          <Space>
            <Button
              danger
              loading={submitting}
              onClick={() => void submitAction('reject')}
            >
              Отказать
            </Button>
            <Button loading={submitting} onClick={() => void submitAction('edit')}>
              Редактировать
            </Button>
            <Button
              type="primary"
              loading={submitting}
              onClick={() => void submitAction('approve')}
            >
              Утвердить
            </Button>
          </Space>
        }
      >
        {selected ? (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <Typography.Text>
              Клиент: <Typography.Text strong>{selected.client_name}</Typography.Text>
              {' · '}
              Тип: {TYPE_LABEL[selected.request_type] ?? selected.request_type}
            </Typography.Text>
            <Table
              rowKey={(item) => `${item.product_code}-${item.warehouse_code}`}
              pagination={false}
              size="small"
              dataSource={editableItems}
              columns={[
                { title: 'Артикул', dataIndex: 'product_code', width: 100 },
                { title: 'Название', dataIndex: 'product_name' },
                { title: 'Склад', dataIndex: 'warehouse_name', width: 140 },
                { title: 'Запрос', dataIndex: 'quantity_requested', width: 90 },
                {
                  title: 'Утв.',
                  dataIndex: 'quantity_approved_input',
                  width: 120,
                  render: (_value, record, index) => (
                    <InputNumber
                      min={0.01}
                      value={record.quantity_approved_input}
                      onChange={(value) => {
                        setEditableItems((current) =>
                          current.map((item, itemIndex) =>
                            itemIndex === index
                              ? {
                                  ...item,
                                  quantity_approved_input: Number(value ?? 0),
                                }
                              : item,
                          ),
                        )
                      }}
                    />
                  ),
                },
                { title: 'Ед', dataIndex: 'unit', width: 70 },
              ]}
            />
            <Input.TextArea
              rows={3}
              placeholder="Комментарий"
              value={comment}
              onChange={(event) => setComment(event.target.value)}
            />
          </Space>
        ) : null}
      </Modal>
    </Space>
  )
}
