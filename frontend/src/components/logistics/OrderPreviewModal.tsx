import { Button, Checkbox, Modal, Space, Table, Typography } from 'antd'
import { DownloadOutlined, DownOutlined, RightOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useMemo, useState } from 'react'
import type { GeneratedOrder, GeneratedOrderItem } from '../../api/types'
import {
  itemDeficitKg,
  orderRouteKey,
  routeTotalKg,
} from '../../utils/b2b'

function positionsLabel(count: number): string {
  const mod10 = count % 10
  const mod100 = count % 100
  if (mod10 === 1 && mod100 !== 11) {
    return 'позиция'
  }
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
    return 'позиции'
  }
  return 'позиций'
}

function formatQty(value: number, digits = 2): string {
  return new Intl.NumberFormat('ru-RU', {
    maximumFractionDigits: digits,
  }).format(value)
}

function routeTitle(route: GeneratedOrder): string {
  return `${route.plant_name} → ${route.warehouse_name}`
}

const detailColumns: ColumnsType<GeneratedOrderItem> = [
  { title: 'Артикул', dataIndex: 'product_code', width: 110 },
  { title: 'Название', dataIndex: 'product_name' },
  {
    title: 'Дефицит (шт)',
    dataIndex: 'deficit',
    width: 130,
    render: (value: number) => formatQty(value),
  },
  {
    title: 'Дефицит (кг)',
    key: 'deficit_kg',
    width: 130,
    render: (_, record) => formatQty(itemDeficitKg(record)),
  },
]

interface OrderPreviewModalProps {
  open: boolean
  routes: GeneratedOrder[]
  exporting?: boolean
  onClose: () => void
  onConfirm: () => void
  onExportB2B: (routes: GeneratedOrder[]) => void
}

export function OrderPreviewModal({
  open,
  routes,
  exporting = false,
  onClose,
  onConfirm,
  onExportB2B,
}: OrderPreviewModalProps) {
  const [selectedKeys, setSelectedKeys] = useState<string[]>([])
  const [expandedKeys, setExpandedKeys] = useState<string[]>([])

  useEffect(() => {
    if (!open) {
      return
    }
    setSelectedKeys(routes.map(orderRouteKey))
    setExpandedKeys([])
  }, [open, routes])

  const selectedSet = useMemo(() => new Set(selectedKeys), [selectedKeys])
  const expandedSet = useMemo(() => new Set(expandedKeys), [expandedKeys])
  const allSelected = routes.length > 0 && selectedKeys.length === routes.length
  const someSelected = selectedKeys.length > 0 && selectedKeys.length < routes.length

  const handleSelectAll = (checked: boolean) => {
    setSelectedKeys(checked ? routes.map(orderRouteKey) : [])
  }

  const handleRouteSelect = (routeKey: string, checked: boolean) => {
    setSelectedKeys((current) =>
      checked
        ? current.includes(routeKey)
          ? current
          : [...current, routeKey]
        : current.filter((key) => key !== routeKey),
    )
  }

  const toggleExpanded = (routeKey: string) => {
    setExpandedKeys((current) =>
      current.includes(routeKey)
        ? current.filter((key) => key !== routeKey)
        : [...current, routeKey],
    )
  }

  const handleExportB2B = () => {
    onExportB2B(routes.filter((route) => selectedSet.has(orderRouteKey(route))))
  }

  return (
    <Modal
      title="📦 Предпросмотр заказов"
      open={open}
      onCancel={onClose}
      width={800}
      destroyOnHidden
      footer={
        <Space>
          <Button onClick={onClose}>Отмена</Button>
          <Button
            type="primary"
            icon={<DownloadOutlined />}
            loading={exporting}
            disabled={selectedKeys.length === 0}
            onClick={handleExportB2B}
          >
            Выгрузить для B2B ({selectedKeys.length} маршрутов)
          </Button>
          <Button type="primary" onClick={onConfirm}>
            Подтвердить
          </Button>
        </Space>
      }
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Checkbox
          checked={allSelected}
          indeterminate={someSelected}
          disabled={routes.length === 0}
          onChange={(event) => handleSelectAll(event.target.checked)}
        >
          Выбрать все маршруты
        </Checkbox>
        <div>
          {routes.map((route) => {
            const key = orderRouteKey(route)
            const title = routeTitle(route)
            const totalKg = routeTotalKg(route)
            const expanded = expandedSet.has(key)
            return (
              <div key={key} style={{ marginBottom: 8 }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 4 }}>
                  <Button
                    type="text"
                    size="small"
                    aria-expanded={expanded}
                    aria-label={
                      expanded ? `Скрыть позиции: ${title}` : `Показать позиции: ${title}`
                    }
                    icon={expanded ? <DownOutlined /> : <RightOutlined />}
                    onClick={() => toggleExpanded(key)}
                  />
                  <Checkbox
                    checked={selectedSet.has(key)}
                    onChange={(event) => handleRouteSelect(key, event.target.checked)}
                  >
                    {title}
                    <Typography.Text type="secondary" style={{ marginLeft: 8 }}>
                      ({route.items.length} {positionsLabel(route.items.length)},{' '}
                      {formatQty(totalKg)} кг)
                    </Typography.Text>
                  </Checkbox>
                </div>
                {expanded ? (
                  <div style={{ marginLeft: 32, marginTop: 8 }}>
                    <Table
                      rowKey="product_code"
                      pagination={false}
                      size="small"
                      dataSource={route.items}
                      columns={detailColumns}
                    />
                  </div>
                ) : null}
              </div>
            )
          })}
        </div>
      </Space>
    </Modal>
  )
}
