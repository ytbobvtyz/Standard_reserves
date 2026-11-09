import { Button, DatePicker, Input, InputNumber, Modal, Space, Table, Tag, Tooltip, Typography, message } from 'antd'
import type { Dayjs } from 'dayjs'
import dayjs from 'dayjs'
import { useEffect, useMemo, useState } from 'react'
import { referencesApi } from '../../api/references'
import { requestsApi } from '../../api/requests'
import type { OverlappingRequestRef } from '../../api/types'
import { OverlappingNormativesNotice } from '../requests/OverlappingNormatives'
import type {
  ApprovalAction,
  ApprovalActionPayload,
  ApprovalPendingItem,
  ApprovalPendingRequest,
  RequestType,
} from '../../api/types'
import {
  ECONOMY_EXPIRY_HINT,
  EXPIRY_ERROR,
  EXPIRY_HINT,
  EXPIRY_TOO_SOON,
  expiryDecreaseError,
  isExpiryDecreaseInvalid,
  isExpiryTooFar,
  isExpiryTooSoon,
  maxExpiryDate,
  minExpiryDate,
} from '../../utils/expiryDate'
import { formatQuantity } from '../../utils/quantity'
import {
  DEFAULT_COVERAGE_THRESHOLDS,
  compareCoverageRows,
  coverageContext,
  coverageLevel,
  coverageMonths,
  coverageSummary,
  formatCoverage,
  needsReview,
  stockAfterApproval,
  type CoverageThresholds,
} from '../../utils/coverage'
import {
  calculateRequirement,
  categoryLabel,
  distanceLabel,
  formatRequirementQty,
  requirementTooltip,
} from '../../utils/requirement'

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
  stage?: 'pp' | 'economy'
  onCancel: () => void
  onSubmit: (payload: ApprovalActionPayload) => Promise<void> | void
}

export function ApprovalModal({
  request,
  submitting,
  stage = 'pp',
  onCancel,
  onSubmit,
}: ApprovalModalProps) {
  const [editableItems, setEditableItems] = useState<EditableItem[]>([])
  const [comment, setComment] = useState('')
  const [expiryDate, setExpiryDate] = useState<Dayjs | null>(null)
  const [overlaps, setOverlaps] = useState<OverlappingRequestRef[]>([])
  const [thresholds, setThresholds] = useState<CoverageThresholds>(
    DEFAULT_COVERAGE_THRESHOLDS,
  )

  useEffect(() => {
    let cancelled = false
    void referencesApi
      .getParams()
      .then(({ data }) => {
        if (cancelled) {
          return
        }
        setThresholds({
          highMonths: Number(data.data.coverage_high_months),
          lowMonths: Number(data.data.coverage_low_months),
        })
      })
      .catch(() => {
        if (!cancelled) {
          setThresholds(DEFAULT_COVERAGE_THRESHOLDS)
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!request) {
      setEditableItems([])
      setComment('')
      setExpiryDate(null)
      setOverlaps([])
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
    if (request.request_type !== 'normative' || !request.client_id) {
      setOverlaps([])
      return
    }
    let cancelled = false
    void requestsApi
      .overlapping({
        client_id: request.client_id,
        exclude_request_id: request.id,
        items: request.items.map((item) => ({
          product_code: item.product_code,
          warehouse_code: item.warehouse_code,
        })),
      })
      .then(({ data }) => {
        if (!cancelled) {
          setOverlaps(data.data.requests)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setOverlaps([])
        }
      })
    return () => {
      cancelled = true
    }
  }, [request])

  const isNormative = request?.request_type === 'normative'
  const isEconomy = stage === 'economy'
  const maxDate = maxExpiryDate(request?.created_at)
  const minDate = minExpiryDate(request?.created_at)
  const currentExpiry = request?.expiry_date

  const rowOrder = useMemo(() => {
    if (!request) {
      return []
    }
    const monthsOf = (item: ApprovalPendingItem) =>
      coverageMonths(
        stockAfterApproval({
          requestType: request.request_type,
          autoComplete: Boolean(request.auto_complete_previous),
          quantity: item.quantity_approved ?? item.quantity_requested,
          existingNz: item.coverage?.existing_nz ?? null,
        }),
        item.coverage?.monthly_sales ?? null,
      )
    return [...request.items]
      .sort((left, right) =>
        compareCoverageRows(monthsOf(left), monthsOf(right), thresholds),
      )
      .map((item) => `${item.product_code}-${item.warehouse_code}`)
  }, [request, thresholds])

  const orderedItems = useMemo(() => {
    const byKey = new Map(
      editableItems.map((item) => [
        `${item.product_code}-${item.warehouse_code}`,
        item,
      ]),
    )
    const seen = new Set(rowOrder)
    return [
      ...rowOrder
        .map((key) => byKey.get(key))
        .filter((item): item is EditableItem => item != null),
      ...editableItems.filter(
        (item) => !seen.has(`${item.product_code}-${item.warehouse_code}`),
      ),
    ]
  }, [editableItems, rowOrder])

  const submitAction = async (action: ApprovalAction) => {
    if (!request) {
      return
    }
    if (action === 'reject' && !comment.trim()) {
      message.error('Комментарий обязателен при отказе')
      return
    }
    if (action === 'approve') {
      const invalid = editableItems.some((item) => item.quantity_approved_input <= 0)
      if (invalid) {
        message.error('Утвержденное количество должно быть больше 0')
        return
      }
      if (isNormative && isExpiryTooSoon(expiryDate, request.created_at)) {
        message.error(EXPIRY_TOO_SOON)
        return
      }
      if (isNormative && isEconomy && isExpiryDecreaseInvalid(expiryDate, currentExpiry)) {
        message.error(expiryDecreaseError(expiryDate, currentExpiry) ?? EXPIRY_ERROR)
        return
      }
      if (isNormative && !isEconomy && isExpiryTooFar(expiryDate, request.created_at)) {
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

  const reviewCount = request
    ? orderedItems.filter((item) =>
        needsReview(
          coverageMonths(
            stockAfterApproval({
              requestType: request.request_type,
              autoComplete: Boolean(request.auto_complete_previous),
              quantity: item.quantity_approved_input,
              existingNz: item.coverage?.existing_nz ?? null,
            }),
            item.coverage?.monthly_sales ?? null,
          ),
          thresholds,
        ),
      ).length
    : 0

  return (
    <Modal
      title={
        request
          ? `Согласование запроса №${request.id.slice(0, 8)}`
          : 'Согласование запроса'
      }
      open={Boolean(request)}
      onCancel={onCancel}
      width={1100}
      footer={
        <Space>
          <Button danger loading={submitting} onClick={() => void submitAction('reject')}>
            Отказать
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
          {isNormative && (request.auto_complete_previous || overlaps.length > 0) ? (
            <OverlappingNormativesNotice
              mode={request.auto_complete_previous ? 'complete' : 'increase'}
              requests={overlaps}
            />
          ) : null}
          {isNormative ? (
            <div>
              <Typography.Text>Срок действия</Typography.Text>
              <DatePicker
                style={{ width: '100%', marginTop: 8 }}
                value={expiryDate}
                disabledDate={(current) => {
                  if (!current) {
                    return false
                  }
                  if (current.isBefore(minDate, 'day')) {
                    return true
                  }
                  if (isEconomy) {
                    return (
                      current.isBefore(dayjs(), 'day') ||
                      Boolean(
                        currentExpiry && current.isAfter(dayjs(currentExpiry), 'day'),
                      )
                    )
                  }
                  return current.isAfter(maxDate, 'day')
                }}
                onChange={(value) => setExpiryDate(value)}
              />
              <Typography.Text type="secondary">
                {isEconomy ? ECONOMY_EXPIRY_HINT : EXPIRY_HINT}
              </Typography.Text>
              {isEconomy && isExpiryDecreaseInvalid(expiryDate, currentExpiry) ? (
                <Typography.Text type="danger" style={{ display: 'block' }}>
                  {expiryDecreaseError(expiryDate, currentExpiry)}
                </Typography.Text>
              ) : null}
              {isExpiryTooSoon(expiryDate, request.created_at) ? (
                <Typography.Text type="danger" style={{ display: 'block' }}>
                  {EXPIRY_TOO_SOON}
                </Typography.Text>
              ) : null}
              {!isEconomy && isExpiryTooFar(expiryDate, request.created_at) ? (
                <Typography.Text type="danger" style={{ display: 'block' }}>
                  {EXPIRY_ERROR}
                </Typography.Text>
              ) : null}
            </div>
          ) : null}
          <Typography.Text type={reviewCount > 0 ? 'danger' : 'secondary'}>
            {coverageSummary(reviewCount, orderedItems.length)}
          </Typography.Text>
          <Table
            rowKey={(item) => `${item.product_code}-${item.warehouse_code}`}
            pagination={false}
            size="small"
            dataSource={orderedItems}
            scroll={{ x: 'max-content' }}
            columns={[
              { title: 'Артикул', dataIndex: 'product_code', width: 100 },
              { title: 'Название', dataIndex: 'product_name' },
              { title: 'Склад', dataIndex: 'warehouse_name', width: 140 },
              { title: 'Запрос', dataIndex: 'quantity_requested', width: 90 },
              {
                title: 'Количество',
                dataIndex: 'quantity_approved_input',
                width: 140,
                render: (_value, record) => (
                  <InputNumber
                    min={record.unit === 'т' ? 0.000001 : 0.01}
                    precision={record.unit === 'т' ? 6 : undefined}
                    value={record.quantity_approved_input}
                    onChange={(value) => {
                      setEditableItems((current) =>
                        current.map((item) =>
                          item.product_code === record.product_code &&
                          item.warehouse_code === record.warehouse_code
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
              ...(isNormative
                ? [
                    {
                      title: 'Категория',
                      width: 110,
                      render: (_: unknown, record: EditableItem) =>
                        categoryLabel(record.category),
                    },
                    {
                      title: 'Удалённость',
                      width: 120,
                      render: (_: unknown, record: EditableItem) =>
                        distanceLabel(Boolean(record.long_distance)),
                    },
                    {
                      title: 'Потребность',
                      width: 140,
                      render: (_: unknown, record: EditableItem) => {
                        const qty = record.quantity_approved_input
                        const requirement = calculateRequirement(
                          qty,
                          record.category,
                          record.long_distance,
                        )
                        return (
                          <Tooltip
                            title={requirementTooltip(
                              qty,
                              record.unit,
                              record.category,
                              record.long_distance,
                            )}
                          >
                            <span>
                              {requirement == null
                                ? '—'
                                : `${formatRequirementQty(requirement)} ${record.unit}`}
                            </span>
                          </Tooltip>
                        )
                      },
                    },
                  ]
                : []),
              {
                title: 'Покрытие',
                width: 150,
                render: (_: unknown, record: EditableItem) => {
                  if (!request) {
                    return null
                  }
                  const stock = stockAfterApproval({
                    requestType: request.request_type,
                    autoComplete: Boolean(request.auto_complete_previous),
                    quantity: record.quantity_approved_input,
                    existingNz: record.coverage?.existing_nz ?? null,
                  })
                  const sales = record.coverage?.monthly_sales ?? null
                  const months = coverageMonths(stock, sales)
                  const level = coverageLevel(months, thresholds)
                  const lines = [
                    sales == null
                      ? 'Реализации клиента по этому артикулу со склада нет.'
                      : `Реализация ${formatQuantity(sales, record.unit)} ${record.unit}/мес.`,
                  ]
                  if (request.request_type === 'one_time') {
                    lines.push(
                      `Перемещение ${formatQuantity(record.quantity_approved_input, record.unit)} ${record.unit}.`,
                    )
                  } else if (!request.auto_complete_previous) {
                    lines.push(
                      `Действующий норматив ${formatQuantity(record.coverage?.existing_nz, record.unit)} ${record.unit}. После утверждения ${formatQuantity(stock, record.unit)} ${record.unit}.`,
                    )
                  } else {
                    lines.push(
                      `После утверждения ${formatQuantity(stock, record.unit)} ${record.unit}.`,
                    )
                  }
                  const extra = coverageContext({
                    stock,
                    monthlySales: sales,
                    warehouseMonthlySales:
                      record.coverage?.warehouse_monthly_sales ?? null,
                    productMonthlySales:
                      record.coverage?.product_monthly_sales ?? null,
                    thresholds,
                  })
                  if (extra) {
                    lines.push(extra)
                  }
                  const label = formatCoverage(months)
                  const marked = level === 'high' || level === 'low' || level === 'none'
                  return (
                    <Tooltip title={lines.join(' ')}>
                      {marked ? (
                        <Tag color={level === 'high' ? 'success' : 'error'}>{label}</Tag>
                      ) : (
                        <span>{label}</span>
                      )}
                    </Tooltip>
                  )
                },
              },
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
