import {
  Button,
  Collapse,
  Empty,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tabs,
  Typography,
  message,
} from 'antd'
import { DownloadOutlined, SendOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getApiErrorMessage } from '../api/client'
import { logisticsApi } from '../api/logistics'
import { referencesApi } from '../api/references'
import type {
  DeficitItem,
  FilterMode,
  GeneratedOrder,
  ObjectListItem,
  Unit,
  WarehouseDeficit,
} from '../api/types'
import { DeficitIndicator } from '../components/logistics/DeficitIndicator'
import { FilterToggle } from '../components/logistics/FilterToggle'
import { UnitToggle } from '../components/logistics/UnitToggle'

function formatQty(value: number, unit: Unit): string {
  return new Intl.NumberFormat('ru-RU', {
    maximumFractionDigits: unit === 'т' ? 4 : 2,
  }).format(value)
}

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

function matchesSearch(item: DeficitItem, search: string): boolean {
  if (!search) {
    return true
  }
  const term = search.trim().toLowerCase()
  return (
    String(item.product_code).includes(term) ||
    item.product_name.toLowerCase().includes(term)
  )
}

export function LogisticsDashboardPage() {
  const navigate = useNavigate()
  const [unit, setUnit] = useState<Unit>('шт')
  const [filterMode, setFilterMode] = useState<FilterMode>('all')
  const [warehouseCode, setWarehouseCode] = useState<number | undefined>()
  const [search, setSearch] = useState('')
  const [warehouses, setWarehouses] = useState<ObjectListItem[]>([])
  const [items, setItems] = useState<WarehouseDeficit[]>([])
  const [summary, setSummary] = useState({
    total_deficit: 0,
    deficit_warehouses: 0,
    deficit_products: 0,
  })
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [orders, setOrders] = useState<GeneratedOrder[]>([])
  const [confirmedOrders, setConfirmedOrders] = useState<GeneratedOrder[]>([])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await logisticsApi.getDashboard({
        unit,
        filter_mode: filterMode,
        warehouse_code: warehouseCode,
      })
      setItems(data.data)
      setSummary(data.summary)
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось загрузить дашборд'))
    } finally {
      setLoading(false)
    }
  }, [unit, filterMode, warehouseCode])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    void referencesApi
      .getObjects({ type: 'warehouse', is_active: true, limit: 100 })
      .then(({ data }) => setWarehouses(data.data))
      .catch((error) => {
        message.error(getApiErrorMessage(error, 'Не удалось загрузить склады'))
      })
  }, [])

  const visibleWarehouses = useMemo(() => {
    return items
      .map((warehouse) => ({
        ...warehouse,
        deficit_items: warehouse.deficit_items.filter((item) =>
          matchesSearch(item, search),
        ),
      }))
      .filter((warehouse) => warehouse.deficit_items.length > 0)
  }, [items, search])

  const columns: ColumnsType<DeficitItem> = [
    { title: 'Артикул', dataIndex: 'product_code', width: 110 },
    { title: 'Название', dataIndex: 'product_name' },
    {
      title: 'Норматив',
      dataIndex: 'normative_quantity',
      width: 120,
      render: (value: number) => formatQty(value, unit),
    },
    {
      title: 'Факт',
      dataIndex: 'fact_quantity',
      width: 120,
      render: (value: number) => formatQty(value, unit),
    },
    {
      title: 'Дефицит',
      dataIndex: 'deficit',
      width: 140,
      render: (value: number, record) => (
        <DeficitIndicator deficit={value} status={record.status} unit={record.unit} />
      ),
    },
    { title: 'Ед', dataIndex: 'unit', width: 70 },
    { title: 'Клиент', dataIndex: 'client_name' },
  ]

  const generateForWarehouses = async (codes: number[]) => {
    if (codes.length === 0) {
      message.info('Нет складов с дефицитом для формирования заказов')
      return
    }
    setGenerating(true)
    try {
      const results = await Promise.all(
        codes.map((code) => logisticsApi.generateOrders(code)),
      )
      const collected = results.flatMap((result) => result.data.data.orders)
      if (collected.length === 0) {
        message.info('Нет позиций с дефицитом')
        return
      }
      setOrders(collected)
      setModalOpen(true)
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось сформировать заказы'))
    } finally {
      setGenerating(false)
    }
  }

  const handleExport = async (codes?: number[]) => {
    setExporting(true)
    try {
      const warehouse =
        codes?.length === 1 ? codes[0] : warehouseCode
      const { data } = await logisticsApi.exportOrders({
        unit,
        warehouse_code: warehouse,
      })
      downloadBlob(data, 'orders.xlsx')
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось выгрузить Excel'))
    } finally {
      setExporting(false)
    }
  }

  const deficitWarehouseCodes = visibleWarehouses
    .filter(
      (item) =>
        item.deficit_count > 0 ||
        item.deficit_items.some((row) => row.deficit > 0),
    )
    .map((item) => item.warehouse_code)

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Tabs
        activeKey="normative"
        onChange={(key) => {
          if (key === 'one-time') {
            navigate('/logistics/one-time')
          }
        }}
        items={[
          { key: 'normative', label: 'Нормативы' },
          { key: 'one-time', label: 'Разовые перемещения' },
        ]}
      />
      <Space wrap style={{ justifyContent: 'space-between', width: '100%' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>
          Дашборд логиста
        </Typography.Title>
        <Typography.Text type="secondary">
          Дефицит: {formatQty(summary.total_deficit, unit)} {unit} · склады:{' '}
          {summary.deficit_warehouses} · позиции: {summary.deficit_products}
        </Typography.Text>
      </Space>
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        <UnitToggle value={unit} onChange={setUnit} />
        <FilterToggle value={filterMode} onChange={setFilterMode} />
        <Space wrap>
          <Input.Search
            allowClear
            placeholder="Поиск по артикулу или названию"
            style={{ width: 320 }}
            onSearch={setSearch}
          />
          <Select
            allowClear
            placeholder="Склад"
            style={{ width: 240 }}
            value={warehouseCode}
            onChange={(value) => setWarehouseCode(value)}
            options={warehouses.map((item) => ({
              value: item.code,
              label: `${item.code} · ${item.name}`,
            }))}
          />
        </Space>
      </Space>
      {visibleWarehouses.length === 0 && !loading ? (
        <Empty description="Складов с выбранным фильтром не найдено" />
      ) : (
        <Collapse
          key={visibleWarehouses.map((item) => item.warehouse_code).join('-')}
          defaultActiveKey={visibleWarehouses.map((item) =>
            String(item.warehouse_code),
          )}
          items={visibleWarehouses.map((warehouse) => ({
            key: String(warehouse.warehouse_code),
            label: (
              <Space>
                <DeficitIndicator
                  deficit={warehouse.total_deficit}
                  status={warehouse.total_deficit > 0 ? 'warning' : 'ok'}
                  unit={unit}
                />
                <Typography.Text strong>{warehouse.warehouse_name}</Typography.Text>
                <Typography.Text type="secondary">
                  дефицит: {warehouse.deficit_count} позиций,{' '}
                  {formatQty(warehouse.total_deficit, unit)} {unit}
                </Typography.Text>
              </Space>
            ),
            children: (
              <Table
                rowKey={(item) => `${item.product_code}-${item.client_name}`}
                loading={loading}
                pagination={false}
                size="small"
                columns={columns}
                dataSource={warehouse.deficit_items}
              />
            ),
          }))}
        />
      )}
      <Button
        type="primary"
        icon={<SendOutlined />}
        loading={generating}
        onClick={() => void generateForWarehouses(deficitWarehouseCodes)}
      >
        Сформировать заказы на все склады
      </Button>
      {confirmedOrders.length > 0 ? (
        <Space direction="vertical">
          <Typography.Text>
            Сформировано: {confirmedOrders.length} заказ(ов)
          </Typography.Text>
          <Button
            icon={<DownloadOutlined />}
            loading={exporting}
            onClick={() => void handleExport()}
          >
            Скачать Excel
          </Button>
        </Space>
      ) : null}
      <Modal
        title="Сформировать заказы"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        width={820}
        footer={
          <Space>
            <Button
              icon={<DownloadOutlined />}
              loading={exporting}
              onClick={() =>
                void handleExport([...new Set(orders.map((item) => item.warehouse_code))])
              }
            >
              Скачать Excel
            </Button>
            <Button
              type="primary"
              onClick={() => {
                setConfirmedOrders(orders)
                setModalOpen(false)
                message.success('Заказы подтверждены')
              }}
            >
              Подтвердить
            </Button>
          </Space>
        }
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          {orders.map((order) => (
            <div key={`${order.plant_code}-${order.warehouse_code}`}>
              <Typography.Text strong>
                {order.plant_name} → {order.warehouse_name}
              </Typography.Text>
              <Typography.Paragraph type="secondary" style={{ marginBottom: 8 }}>
                Срок поставки: {order.estimated_delivery_days} дн.
              </Typography.Paragraph>
              <Table
                rowKey="product_code"
                pagination={false}
                size="small"
                dataSource={order.items}
                columns={[
                  { title: 'Артикул', dataIndex: 'product_code', width: 110 },
                  { title: 'Название', dataIndex: 'product_name' },
                  {
                    title: 'Дефицит',
                    dataIndex: 'deficit',
                    width: 120,
                    render: (value: number) => formatQty(value, 'шт'),
                  },
                  { title: 'Ед', dataIndex: 'unit', width: 70 },
                ]}
              />
            </div>
          ))}
        </Space>
      </Modal>
    </Space>
  )
}
