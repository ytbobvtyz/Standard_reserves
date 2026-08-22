import {
  Button,
  Checkbox,
  Collapse,
  Empty,
  Input,
  Modal,
  Progress,
  Select,
  Space,
  Spin,
  Table,
  Tabs,
  Typography,
  Upload,
  message,
} from 'antd'
import { DownloadOutlined, SendOutlined, UploadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getApiErrorMessage } from '../api/client'
import { logisticsApi } from '../api/logistics'
import { referencesApi } from '../api/references'
import type {
  BalanceSyncInfo,
  BalanceUploadResult,
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
import { useAuthStore } from '../stores/auth'

function formatQty(value: number, unit: Unit): string {
  return new Intl.NumberFormat('ru-RU', {
    maximumFractionDigits: unit === 'т' ? 4 : 2,
  }).format(value)
}

function QuantityCell({ value, unit }: { value: number; unit: Unit }) {
  return (
    <span style={value < 0 ? { color: '#cf1322', fontWeight: 600 } : undefined}>
      {formatQty(value, unit)}
    </span>
  )
}

function sumItems(
  items: DeficitItem[],
  field: 'normative_quantity' | 'available' | 'plan',
): number {
  return items.reduce((total, item) => total + item[field], 0)
}

const KG_IN_TON = 1000

function quantize(value: number, unit: Unit): number {
  const factor = unit === 'т' ? 10000 : 100
  return Math.round(value * factor) / factor
}

function fromPieces(quantityPcs: number, unit: Unit, weightKg: number): number {
  if (unit === 'шт') {
    return quantize(quantityPcs, unit)
  }
  if (weightKg <= 0) {
    return 0
  }
  return quantize((quantityPcs * weightKg) / KG_IN_TON, unit)
}

function convertItem(item: DeficitItem, unit: Unit): DeficitItem {
  const weightKg = item.weight_kg ?? 0
  return {
    ...item,
    unit,
    normative_quantity: fromPieces(item.normative_quantity, unit, weightKg),
    available: fromPieces(item.available, unit, weightKg),
    plan: fromPieces(item.plan, unit, weightKg),
    deficit: fromPieces(item.deficit, unit, weightKg),
  }
}

function matchesFilter(item: DeficitItem, filterMode: FilterMode): boolean {
  if (filterMode === 'deficit_only') {
    return item.deficit > 0
  }
  if (filterMode === 'with_normatives') {
    return item.normative_quantity > 0
  }
  return true
}

function warehouseMetrics(items: DeficitItem[]) {
  const positive = items.filter((item) => item.deficit > 0)
  return {
    total_deficit: positive.reduce((total, item) => total + item.deficit, 0),
    deficit_count: positive.length,
  }
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

function formatShortName(fullName: string): string {
  const parts = fullName.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) {
    return fullName
  }
  if (parts.length === 1) {
    return parts[0]
  }
  return `${parts[0]} ${parts[1].charAt(0)}.`
}

function formatSyncAt(value: string): string {
  return new Date(value).toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function LogisticsDashboardPage() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const canManage = user?.role === 'logistics'
  const [unit, setUnit] = useState<Unit>('шт')
  const [filterMode, setFilterMode] = useState<FilterMode>('all')
  const [warehouseCode, setWarehouseCode] = useState<number | undefined>()
  const [search, setSearch] = useState('')
  const [warehouses, setWarehouses] = useState<ObjectListItem[]>([])
  const [items, setItems] = useState<WarehouseDeficit[]>([])
  const [loading, setLoading] = useState(true)
  const [activeKeys, setActiveKeys] = useState<string[]>([])
  const [generating, setGenerating] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<number | null>(null)
  const [uploadResult, setUploadResult] = useState<BalanceUploadResult | null>(null)
  const [orders, setOrders] = useState<GeneratedOrder[]>([])
  const [confirmedOrders, setConfirmedOrders] = useState<GeneratedOrder[]>([])
  const [selectedWarehouseCodes, setSelectedWarehouseCodes] = useState<number[]>([])
  const [syncInfo, setSyncInfo] = useState<BalanceSyncInfo | null>(null)
  const hasRowsRef = useRef(false)

  const load = useCallback(async () => {
    if (!hasRowsRef.current) {
      setLoading(true)
    }
    try {
      const [{ data }, syncResponse] = await Promise.all([
        logisticsApi.getDashboard({
          unit: 'шт',
          filter_mode: 'all',
        }),
        logisticsApi.getSyncInfo(),
      ])
      setItems(data.data)
      setSyncInfo(syncResponse.data.data)
      hasRowsRef.current = true
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось загрузить дашборд'))
    } finally {
      setLoading(false)
    }
  }, [])

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
      .filter(
        (warehouse) =>
          warehouseCode == null || warehouse.warehouse_code === warehouseCode,
      )
      .map((warehouse) => {
        const deficitItems = warehouse.deficit_items
          .filter(
            (item) =>
              matchesFilter(item, filterMode) && matchesSearch(item, search),
          )
          .map((item) => convertItem(item, unit))
        return {
          ...warehouse,
          deficit_items: deficitItems,
          ...warehouseMetrics(deficitItems),
        }
      })
      .filter((warehouse) => warehouse.deficit_items.length > 0)
  }, [items, warehouseCode, filterMode, search, unit])

  const visibleWarehouseCodes = useMemo(
    () => visibleWarehouses.map((item) => item.warehouse_code),
    [visibleWarehouses],
  )

  const totals = useMemo(() => {
    const rows = visibleWarehouses.flatMap((warehouse) => warehouse.deficit_items)
    const positive = rows.filter((item) => item.deficit > 0)
    return {
      normative: sumItems(rows, 'normative_quantity'),
      available: sumItems(rows, 'available'),
      plan: sumItems(rows, 'plan'),
      deficit: positive.reduce((total, item) => total + item.deficit, 0),
      deficitWarehouses: visibleWarehouses.filter((item) => item.total_deficit > 0)
        .length,
      deficitProducts: new Set(positive.map((item) => item.product_code)).size,
    }
  }, [visibleWarehouses])

  useEffect(() => {
    setSelectedWarehouseCodes((current) =>
      current.filter((code) => visibleWarehouseCodes.includes(code)),
    )
    setActiveKeys((current) =>
      current.filter((key) =>
        visibleWarehouseCodes.includes(Number(key)),
      ),
    )
  }, [visibleWarehouseCodes])

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
      title: 'Доступно',
      dataIndex: 'available',
      width: 120,
      render: (value: number) => <QuantityCell value={value} unit={unit} />,
    },
    {
      title: 'Запланировано',
      dataIndex: 'plan',
      width: 140,
      render: (value: number) => <QuantityCell value={value} unit={unit} />,
    },
    {
      title: 'Дефицит',
      dataIndex: 'deficit',
      width: 140,
      render: (value: number, record) => (
        <DeficitIndicator deficit={value} status={record.status} unit={record.unit} />
      ),
    },
    {
      title: 'Ед',
      width: 80,
      render: (_, record) => record.stock_unit || record.unit,
    },
    { title: 'Клиент', dataIndex: 'client_name' },
  ]

  const generateForWarehouses = async (codes: number[]) => {
    if (codes.length === 0) {
      message.info('Нет складов с дефицитом для формирования заказов')
      return
    }
    setGenerating(true)
    try {
      const { data } = await logisticsApi.generateOrdersBulk({
        warehouse_codes: codes,
      })
      const collected = data.data.orders
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

  const handleUpload = async (file: File) => {
    setUploading(true)
    setUploadProgress(0)
    setUploadResult(null)
    try {
      const { data } = await logisticsApi.uploadBalances(file, setUploadProgress)
      setUploadResult(data.data)
      setUploadProgress(100)
      await load()
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось загрузить остатки'))
    } finally {
      setUploading(false)
    }
    return false
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

  const allVisibleSelected =
    visibleWarehouseCodes.length > 0 &&
    visibleWarehouseCodes.every((code) => selectedWarehouseCodes.includes(code))
  const someVisibleSelected = selectedWarehouseCodes.some((code) =>
    visibleWarehouseCodes.includes(code),
  )

  const toggleWarehouse = (code: number, checked: boolean) => {
    setSelectedWarehouseCodes((current) =>
      checked
        ? current.includes(code)
          ? current
          : [...current, code]
        : current.filter((item) => item !== code),
    )
  }

  const toggleAllVisible = (checked: boolean) => {
    setSelectedWarehouseCodes(checked ? [...visibleWarehouseCodes] : [])
  }

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
        <Space wrap>
          <Typography.Title level={3} style={{ margin: 0 }}>
            Дашборд логиста
          </Typography.Title>
          {canManage ? (
            <Button
              icon={<UploadOutlined aria-hidden />}
              onClick={() => {
                setUploadResult(null)
                setUploadProgress(null)
                setUploadOpen(true)
              }}
            >
              Загрузить актуальные остатки
            </Button>
          ) : null}
        </Space>
        <Space direction="vertical" size={0} align="end">
          <Typography.Text type="secondary">
            Дефицит: {formatQty(totals.deficit, unit)} {unit} · склады:{' '}
            {totals.deficitWarehouses} · позиции: {totals.deficitProducts}
          </Typography.Text>
          <Typography.Text type="secondary">
            Всего норматив: {formatQty(totals.normative, unit)} {unit}
            {' · '}Всего доступно:{' '}
            <QuantityCell value={totals.available} unit={unit} /> {unit}
            {' · '}Всего запланировано:{' '}
            <QuantityCell value={totals.plan} unit={unit} /> {unit}
          </Typography.Text>
        </Space>
      </Space>
      <Space direction="vertical" size={0}>
        {syncInfo?.last_balances_sync_at ? (
          <>
            <Typography.Text>
              📦 Актуальные остатки обновлены:{' '}
              {formatSyncAt(syncInfo.last_balances_sync_at)}
            </Typography.Text>
            <Typography.Text>
              👤 Кто:{' '}
              {syncInfo.last_balances_sync_by
                ? `${formatShortName(syncInfo.last_balances_sync_by.full_name)} (${syncInfo.last_balances_sync_by.role})`
                : 'не указан'}
            </Typography.Text>
          </>
        ) : (
          <Typography.Text type="secondary">
            Актуальные остатки ещё не загружались
          </Typography.Text>
        )}
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
      {loading && items.length === 0 ? (
        <Spin />
      ) : visibleWarehouses.length === 0 ? (
        <Empty description="Складов с выбранным фильтром не найдено" />
      ) : (
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          {canManage ? (
            <Checkbox
              checked={allVisibleSelected}
              indeterminate={someVisibleSelected && !allVisibleSelected}
              disabled={visibleWarehouseCodes.length === 0}
              onChange={(event) => toggleAllVisible(event.target.checked)}
            >
              Выбрать все склады
            </Checkbox>
          ) : null}
          <Collapse
            activeKey={activeKeys}
            onChange={(keys) =>
              setActiveKeys(
                Array.isArray(keys) ? keys.map(String) : [String(keys)],
              )
            }
            items={visibleWarehouses.map((warehouse) => {
              const warehouseKey = String(warehouse.warehouse_code)
              const isOpen = activeKeys.includes(warehouseKey)
              const totalNormative = sumItems(
                warehouse.deficit_items,
                'normative_quantity',
              )
              const totalAvailable = sumItems(warehouse.deficit_items, 'available')
              const totalPlan = sumItems(warehouse.deficit_items, 'plan')
              return {
                key: warehouseKey,
                label: (
                  <Space wrap align="start">
                    {canManage ? (
                      <Checkbox
                        aria-label={`Выбрать ${warehouse.warehouse_name}`}
                        checked={selectedWarehouseCodes.includes(
                          warehouse.warehouse_code,
                        )}
                        onClick={(event) => event.stopPropagation()}
                        onChange={(event) =>
                          toggleWarehouse(
                            warehouse.warehouse_code,
                            event.target.checked,
                          )
                        }
                      />
                    ) : null}
                    <DeficitIndicator
                      deficit={warehouse.total_deficit}
                      status={warehouse.total_deficit > 0 ? 'warning' : 'ok'}
                      unit={unit}
                    />
                    <Space direction="vertical" size={0}>
                      <Typography.Text strong>
                        {warehouse.warehouse_name}
                      </Typography.Text>
                      <Typography.Text type="secondary">
                        дефицит: {warehouse.deficit_count} позиций,{' '}
                        {formatQty(warehouse.total_deficit, unit)} {unit}
                        {' · '}норматив: {formatQty(totalNormative, unit)} {unit}
                        {' · '}доступно:{' '}
                        <QuantityCell value={totalAvailable} unit={unit} /> {unit}
                        {' · '}запланировано:{' '}
                        <QuantityCell value={totalPlan} unit={unit} /> {unit}
                      </Typography.Text>
                    </Space>
                  </Space>
                ),
                children: isOpen ? (
                  <Table
                    rowKey={(item) => `${item.product_code}-${item.client_name}`}
                    pagination={false}
                    size="small"
                    columns={columns}
                    dataSource={warehouse.deficit_items}
                  />
                ) : null,
              }
            })}
          />
        </Space>
      )}
      {canManage ? (
        <Space wrap>
          <Button
            type="primary"
            icon={<SendOutlined />}
            loading={generating}
            disabled={selectedWarehouseCodes.length === 0}
            onClick={() => void generateForWarehouses(selectedWarehouseCodes)}
          >
            Сформировать заказы на выбранные склады
          </Button>
          <Button
            icon={<SendOutlined />}
            loading={generating}
            disabled={visibleWarehouseCodes.length === 0}
            onClick={() => void generateForWarehouses(visibleWarehouseCodes)}
          >
            Сформировать заказы на все склады
          </Button>
        </Space>
      ) : null}
      {canManage && confirmedOrders.length > 0 ? (
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
      <Modal
        title="Загрузить актуальные остатки"
        open={uploadOpen}
        onCancel={() => setUploadOpen(false)}
        footer={null}
        destroyOnHidden
      >
        <Upload.Dragger
          accept=".xlsx,.xls"
          maxCount={1}
          showUploadList={false}
          disabled={uploading}
          beforeUpload={(file) => {
            void handleUpload(file)
            return false
          }}
        >
          <p>Перетащите Excel-файл сюда или нажмите, чтобы выбрать</p>
          <p>.xlsx или .xls</p>
        </Upload.Dragger>
        {uploadProgress !== null ? (
          <Progress percent={uploadProgress} status={uploading ? 'active' : 'success'} />
        ) : null}
        {uploadResult ? (
          <Space direction="vertical" style={{ marginTop: 16, width: '100%' }}>
            <Typography.Text strong>{uploadResult.message}</Typography.Text>
            {uploadResult.error_details.map((item) => (
              <Typography.Text key={item.row} type="danger">
                Строка {item.row}: {item.message}
              </Typography.Text>
            ))}
          </Space>
        ) : null}
      </Modal>
    </Space>
  )
}
