import { Button, DatePicker, Input, InputNumber, Modal, Space, Table, Typography, message } from 'antd'
import type { Dayjs } from 'dayjs'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import type {
  ApprovalAction,
  ApprovalActionPayload,
  ApprovalPendingItem,
  ApprovalPendingRequest,
  RequestType,
} from '../../api/types'
import { EXPIRY_ERROR, EXPIRY_HINT, isExpiryTooFar, maxExpiryDate } from '../../utils/expiryDate'

const TYPE_LABEL: Record<RequestType, string> = {
  normative: 'Норматив',
  one_time: 'Разовое',
}

interface EditableItem extends ApprovalPendingItem {
  quantity_approved_input: number
}

interface ApprovalModalProps {
  request: ApprovalPendingRequest | null
  submitting: boolean
  onCancel: () => void
  onSubmit: (payload: ApprovalActionPayload) => Promise<void> | void
}

export function ApprovalModal({
  request,
  submitting,
  onCancel,
  onSubmit,
}: ApprovalModalProps) {
  const [editableItems, setEditableItems] = useState<EditableItem[]>([])
  const [comment, setComment] = useState('')
  const [expiryDate, setExpiryDate] = useState<Dayjs | null>(null)

  useEffect(() => {
    if (!request) {
      setEditableItems([])
      setComment('')
      setExpiryDate(null)
      return
    }
    setComment('')
    setExpiryDate(request.expiry_date ? dayjs(request.expiry_date) : null)
    setEditableItems(
      request.items.map((item) => ({
        ...item,
        quantity_approved_input: item.quantity_approved ?? item.quantity_requested,
      })),
    )
  }, [request])

  const isNormative = request?.request_type === 'normative'
  const maxDate = maxExpiryDate(request?.created_at)

  const submitAction = async (action: ApprovalAction) => {
    if (!request) {
      return
    }
    if (action === 'reject' && !comment.trim()) {
      message.error('Комментарий обязателен при отказе')
      return
    }
    if (action === 'edit' || action === 'approve') {
      const invalid = editableItems.some((item) => item.quantity_approved_input <= 0)
      if (invalid) {
        message.error('Утвержденное количество должно быть больше 0')
        return
      }
      if (isNormative && isExpiryTooFar(expiryDate, request.created_at)) {
        message.error(EXPIRY_ERROR)
        return
      }
    }

    const itemsPayload = editableItems.map((item) => ({
      product_code: item.product_code,
      warehouse_code: item.warehouse_code,
      quantity_approved: item.quantity_approved_input,
    }))
    const payload: ApprovalActionPayload =
      action === 'reject'
        ? { action, comment: comment.trim() || undefined }
        : {
            action,
            comment: comment.trim() || undefined,
            items: itemsPayload,
            expiry_date:
              isNormative && expiryDate ? expiryDate.format('YYYY-MM-DD') : undefined,
          }

    await onSubmit(payload)
  }

  return (
    <Modal
      title={
        request
          ? `Согласование запроса №${request.id.slice(0, 8)}`
          : 'Согласование запроса'
      }
      open={Boolean(request)}
      onCancel={onCancel}
      width={860}
      footer={
        <Space>
          <Button danger loading={submitting} onClick={() => void submitAction('reject')}>
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
      {request ? (
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Typography.Text>
            Клиент: <Typography.Text strong>{request.client_name}</Typography.Text>
            {' · '}
            Тип: {TYPE_LABEL[request.request_type] ?? request.request_type}
          </Typography.Text>
          {isNormative ? (
            <div>
              <Typography.Text>Срок действия</Typography.Text>
              <DatePicker
                style={{ width: '100%', marginTop: 8 }}
                value={expiryDate}
                disabledDate={(current) =>
                  Boolean(current && current.isAfter(maxDate, 'day'))
                }
                onChange={(value) => setExpiryDate(value)}
              />
              <Typography.Text type="secondary">{EXPIRY_HINT}</Typography.Text>
              {isExpiryTooFar(expiryDate, request.created_at) ? (
                <Typography.Text type="danger" style={{ display: 'block' }}>
                  {EXPIRY_ERROR}
                </Typography.Text>
              ) : null}
            </div>
          ) : null}
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
                title: 'Утверждено',
                dataIndex: 'quantity_approved_input',
                width: 140,
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
  )
}
