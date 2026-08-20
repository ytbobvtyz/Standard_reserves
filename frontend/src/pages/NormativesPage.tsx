import { Card, DatePicker, Input, Select, Space, Table, Typography, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { Dayjs } from 'dayjs'
import dayjs from 'dayjs'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { getApiErrorMessage } from '../api/client'
import { normativesApi } from '../api/normatives'
import { referencesApi } from '../api/references'
import type { NormativeOnDateItem, ObjectListItem, Unit } from '../api/types'

interface NormativeRow {
  key: string
  product_code: number
  product_name: string
  warehouse_code: number
  warehouse_name: string
  quantity: number
  unit: Unit
  client_name: string
  category: string
}

function flattenOnDate(
  items: NormativeOnDateItem[],
  category?: 'A' | 'B' | 'C',
  clientName?: string,
): NormativeRow[] {
  const clientFilter = clientName?.trim().toLowerCase()
  const rows: NormativeRow[] = []
  items.forEach((item, itemIndex) => {
    if (category && item.category && item.category !== category) {
      return
    }
    item.details.forEach((detail, detailIndex) => {
      if (clientFilter && !detail.client_name.toLowerCase().includes(clientFilter)) {
        return
      }
      rows.push({
        key: `${item.warehouse_code}-${item.product_code}-${detailIndex}-${itemIndex}`,
        product_code: item.product_code,
        product_name: item.product_name,
        warehouse_code: item.warehouse_code,
        warehouse_name: item.warehouse_name,
        quantity: detail.quantity,
        unit: item.unit,
        client_name: detail.client_name,
        category: item.category ?? '',
      })
    })
  })
  return rows
}

function formatQty(quantity: number, unit: Unit): string {
  return `${quantity.toLocaleString('ru-RU')} ${unit}`
}

const SEARCH_DEBOUNCE_MS = 400

export function NormativesPage() {
  const [sliceDate, setSliceDate] = useState<Dayjs>(() => dayjs())
  const [warehouseCode, setWarehouseCode] = useState<number | undefined>()
  const [category, setCategory] = useState<'A' | 'B' | 'C' | undefined>()
  const [clientName, setClientName] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [warehouses, setWarehouses] = useState<ObjectListItem[]>([])
  const [items, setItems] = useState<NormativeOnDateItem[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(searchInput.trim())
    }, SEARCH_DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [searchInput])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await normativesApi.getOnDate({
        date: sliceDate.format('YYYY-MM-DD'),
        warehouse_code: warehouseCode,
        search: search || undefined,
      })
      setItems(data.data)
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось загрузить нормативы'))
    } finally {
      setLoading(false)
    }
  }, [sliceDate, warehouseCode, search])

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

  const rows = useMemo(
    () => flattenOnDate(items, category, clientName),
    [items, category, clientName],
  )

  const totals = useMemo(() => {
    const byWarehouse = new Map<string, Map<Unit, number>>()
    for (const row of rows) {
      const units = byWarehouse.get(row.warehouse_name) ?? new Map<Unit, number>()
      units.set(row.unit, (units.get(row.unit) ?? 0) + row.quantity)
      byWarehouse.set(row.warehouse_name, units)
    }
    return [...byWarehouse.entries()].map(([name, units]) => ({
      name,
      label: [...units.entries()]
        .map(([unit, quantity]) => formatQty(quantity, unit))
        .join(', '),
    }))
  }, [rows])

  const columns: ColumnsType<NormativeRow> = [
    { title: 'Артикул', dataIndex: 'product_code', width: 110 },
    { title: 'Название', dataIndex: 'product_name' },
    { title: 'Склад', dataIndex: 'warehouse_name' },
    {
      title: 'Количество',
      key: 'quantity',
      width: 140,
      render: (_, record) => formatQty(record.quantity, record.unit),
    },
    { title: 'Клиент', dataIndex: 'client_name' },
  ]

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={3}>Нормативы</Typography.Title>
      <Space wrap>
        <Input
          allowClear
          placeholder="Поиск по артикулу или названию"
          style={{ width: 280 }}
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          aria-label="Поиск по артикулу или названию"
        />
        <DatePicker
          allowClear={false}
          value={sliceDate}
          onChange={(value) => {
            if (value) {
              setSliceDate(value)
            }
          }}
          aria-label="Срез на дату"
          placeholder="Срез на дату"
        />
        <Select
          allowClear
          aria-label="Склад"
          placeholder="Склад"
          style={{ width: 220 }}
          value={warehouseCode}
          onChange={(value) => setWarehouseCode(value)}
          options={warehouses.map((item) => ({
            value: item.code,
            label: item.name,
          }))}
        />
        <Select
          allowClear
          aria-label="Категория"
          placeholder="Категория"
          style={{ width: 140 }}
          value={category}
          onChange={(value) => setCategory(value)}
          options={[
            { value: 'A', label: 'A' },
            { value: 'B', label: 'B' },
            { value: 'C', label: 'C' },
          ]}
        />
        <Input
          allowClear
          placeholder="Клиент"
          style={{ width: 220 }}
          value={clientName}
          onChange={(event) => setClientName(event.target.value)}
          aria-label="Клиент"
        />
      </Space>
      <Table
        rowKey="key"
        loading={loading}
        dataSource={rows}
        pagination={{ pageSize: 20 }}
        columns={columns}
      />
      <Card title="Итого по складам" size="small">
        {totals.length === 0 ? (
          <Typography.Text type="secondary">Нет данных для агрегации</Typography.Text>
        ) : (
          <Space direction="vertical">
            {totals.map((item) => (
              <Typography.Text key={item.name}>
                {item.name}: {item.label}
              </Typography.Text>
            ))}
          </Space>
        )}
      </Card>
    </Space>
  )
}
