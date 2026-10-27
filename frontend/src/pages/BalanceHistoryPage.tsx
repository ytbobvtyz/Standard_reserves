import { Button, DatePicker, Select, Space, Table, Typography, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { useCallback, useEffect, useState } from 'react'
import { getApiErrorMessage } from '../api/client'
import { logisticsApi } from '../api/logistics'
import { referencesApi } from '../api/references'
import type { BalanceHistoryItem, ObjectListItem } from '../api/types'
import { ProductAutocomplete } from '../components/requests/ProductAutocomplete'
import { formatDateTime } from '../utils/format'

interface FilterState {
  snapshot_date?: string
  warehouse_code?: number
  product_code?: number
}

const columns: ColumnsType<BalanceHistoryItem> = [
  {
    title: 'Склад',
    key: 'warehouse',
    render: (_value, row) => `${row.warehouse_code} — ${row.warehouse_name}`,
  },
  {
    title: 'Артикул',
    key: 'product',
    render: (_value, row) => `${row.product_code} — ${row.product_name}`,
  },
  { title: 'Доступно', dataIndex: 'available', width: 120 },
  { title: 'План', dataIndex: 'plan', width: 120 },
  { title: 'Единица', dataIndex: 'unit', width: 100 },
  {
    title: 'Загружен',
    dataIndex: 'snapshot_at',
    width: 180,
    render: (value: string) => formatDateTime(value),
  },
]

export function BalanceHistoryPage() {
  const [draft, setDraft] = useState<FilterState>({})
  const [applied, setApplied] = useState<FilterState>({})
  const [warehouses, setWarehouses] = useState<ObjectListItem[]>([])
  const [snapshotDates, setSnapshotDates] = useState<Set<string> | null>(null)
  const [items, setItems] = useState<BalanceHistoryItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const limit = 50

  useEffect(() => {
    let cancelled = false
    void logisticsApi
      .getBalanceSnapshotDates()
      .then(({ data }) => {
        if (!cancelled) {
          setSnapshotDates(new Set(data.data))
        }
      })
      .catch(() => {
        if (!cancelled) {
          message.error('Не удалось загрузить даты снимков')
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    void referencesApi
      .getObjects({ type: 'warehouse', is_active: true, limit: 200 })
      .then(({ data }) => {
        if (!cancelled) {
          setWarehouses(data.data)
        }
      })
      .catch(() => {
        if (!cancelled) {
          message.error('Не удалось загрузить склады')
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  const load = useCallback(async () => {
    if (!applied.snapshot_date) {
      setItems([])
      setTotal(0)
      return
    }
    setLoading(true)
    try {
      const { data } = await logisticsApi.getBalanceHistory({
        date_from: applied.snapshot_date,
        date_to: applied.snapshot_date,
        warehouse_code: applied.warehouse_code,
        product_code: applied.product_code,
        page,
        limit,
      })
      setItems(data.data)
      setTotal(data.meta?.total ?? data.data.length)
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось загрузить снимок остатков'))
    } finally {
      setLoading(false)
    }
  }, [applied, page])

  useEffect(() => {
    void load()
  }, [load])

  const applyFilters = () => {
    setPage(1)
    setApplied({ ...draft })
  }

  const resetFilters = () => {
    setDraft({})
    setApplied({})
    setPage(1)
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={3} style={{ margin: 0 }}>
        История доступных остатков
      </Typography.Title>
      <Typography.Text type="secondary">
        Снимок остатков на выбранную дату
      </Typography.Text>
      <Space wrap>
        <DatePicker
          aria-label="Дата снимка"
          format="DD.MM.YYYY"
          placeholder="Дата снимка"
          allowClear
          disabledDate={(current) =>
            !snapshotDates?.has(current.format('YYYY-MM-DD'))
          }
          value={draft.snapshot_date ? dayjs(draft.snapshot_date) : null}
          onChange={(value) =>
            setDraft((current) => ({
              ...current,
              snapshot_date: value ? value.format('YYYY-MM-DD') : undefined,
            }))
          }
        />
        <Select
          aria-label="Склад"
          allowClear
          showSearch
          optionFilterProp="label"
          placeholder="Склад"
          style={{ width: 280 }}
          value={draft.warehouse_code}
          options={warehouses.map((warehouse) => ({
            value: warehouse.code,
            label: `${warehouse.code} — ${warehouse.name}`,
          }))}
          onChange={(warehouseCode) =>
            setDraft((current) => ({
              ...current,
              warehouse_code: warehouseCode,
            }))
          }
        />
        <div data-testid="product-filter" style={{ width: 280 }}>
          <ProductAutocomplete
            ariaLabel="Артикул"
            value={draft.product_code}
            onChange={(productCode) =>
              setDraft((current) => ({ ...current, product_code: productCode }))
            }
          />
        </div>
        <Button type="primary" onClick={applyFilters}>
          Применить фильтр
        </Button>
        <Button onClick={resetFilters}>Сбросить</Button>
      </Space>
      {applied.snapshot_date ? (
        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={items}
          locale={{ emptyText: 'На эту дату снимка нет' }}
          pagination={{
            current: page,
            pageSize: limit,
            total,
            showSizeChanger: false,
            onChange: (next) => setPage(next),
          }}
        />
      ) : (
        <Typography.Text>Выберите дату снимка</Typography.Text>
      )}
    </Space>
  )
}
