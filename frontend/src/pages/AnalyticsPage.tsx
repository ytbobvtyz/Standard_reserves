import {
  Alert,
  Card,
  Checkbox,
  DatePicker,
  Empty,
  Select,
  Space,
  Spin,
  Typography,
  message,
} from 'antd'
import type { Dayjs } from 'dayjs'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { analyticsApi } from '../api/analytics'
import { getApiErrorMessage } from '../api/client'
import { referencesApi } from '../api/references'
import type {
  AnalyticsFilterClient,
  AnalyticsFilterWarehouse,
  DepartmentListItem,
  StockDynamicsData,
  StockSummaryData,
} from '../api/types'
import { StockDynamicsChart } from '../components/analytics/StockDynamicsChart'
import { StockSummaryTable } from '../components/analytics/StockSummaryTable'
import { ShipmentSelectionTables } from '../components/analytics/ShipmentSelectionTables'
import {
  defaultStockRange,
  type StockGranularity,
} from '../components/analytics/stockDynamics'
import { ProductAutocomplete } from '../components/requests/ProductAutocomplete'

const { RangePicker } = DatePicker

function selectionQuery(
  clientIds: string[] | null,
  warehouseCodes: number[] | null,
): { client_ids?: string[]; warehouse_codes?: number[] } {
  return {
    ...(clientIds !== null ? { client_ids: clientIds } : {}),
    ...(warehouseCodes !== null ? { warehouse_codes: warehouseCodes } : {}),
  }
}

export function AnalyticsPage() {
  const [productCode, setProductCode] = useState<number | undefined>()
  const [departmentId, setDepartmentId] = useState<string | undefined>()
  const [granularity, setGranularity] = useState<StockGranularity>('month')
  const [showFullStock, setShowFullStock] = useState(false)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [rangeMode, setRangeMode] = useState<'auto' | 'manual'>('auto')
  const [departments, setDepartments] = useState<DepartmentListItem[]>([])
  const [filterClients, setFilterClients] = useState<AnalyticsFilterClient[]>([])
  const [filterWarehouses, setFilterWarehouses] = useState<AnalyticsFilterWarehouse[]>([])
  const [selectedClientIds, setSelectedClientIds] = useState<string[] | null>(null)
  const [selectedWarehouseCodes, setSelectedWarehouseCodes] = useState<number[] | null>(null)
  const [series, setSeries] = useState<StockDynamicsData | null>(null)
  const [summary, setSummary] = useState<StockSummaryData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const selectionEmpty =
    selectedClientIds !== null &&
    selectedClientIds.length === 0 &&
    selectedWarehouseCodes !== null &&
    selectedWarehouseCodes.length === 0

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const departmentsResp = await referencesApi.getDepartments({ has_normatives: true })
        if (!cancelled) {
          setDepartments(departmentsResp.data.data)
        }
      } catch (loadError) {
        if (!cancelled) {
          message.error(getApiErrorMessage(loadError, 'Не удалось загрузить фильтры'))
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    setSelectedClientIds(null)
    setSelectedWarehouseCodes(null)
    if (!productCode) {
      setFilterClients([])
      setFilterWarehouses([])
      return
    }
    let cancelled = false
    void (async () => {
      try {
        const response = await analyticsApi.getFilters({ product_code: productCode })
        if (cancelled) {
          return
        }
        setFilterClients(response.data.data.clients)
        setFilterWarehouses(response.data.data.warehouses)
      } catch (loadError) {
        if (!cancelled) {
          setFilterClients([])
          setFilterWarehouses([])
          message.error(getApiErrorMessage(loadError, 'Не удалось загрузить клиентов и склады'))
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [productCode])

  useEffect(() => {
    if (granularity !== 'month' || rangeMode !== 'auto' || selectionEmpty) {
      return
    }
    let cancelled = false
    void (async () => {
      if (!productCode) {
        const today = dayjs().format('YYYY-MM-DD')
        setDateFrom(today)
        setDateTo(today)
        return
      }
      try {
        const response = await analyticsApi.getStockBounds({
          product_code: productCode,
          ...(departmentId ? { department_id: departmentId } : {}),
          ...selectionQuery(selectedClientIds, selectedWarehouseCodes),
        })
        if (cancelled) {
          return
        }
        const range = defaultStockRange(
          'month',
          dayjs(),
          response.data.data.earliest_date,
        )
        setDateFrom(range.from)
        setDateTo(range.to)
      } catch (loadError) {
        if (!cancelled) {
          message.error(getApiErrorMessage(loadError, 'Не удалось определить период'))
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [
    granularity,
    rangeMode,
    productCode,
    departmentId,
    selectedClientIds,
    selectedWarehouseCodes,
    selectionEmpty,
  ])

  useEffect(() => {
    if (!productCode || selectionEmpty) {
      setSummary(null)
      return
    }
    let cancelled = false
    void (async () => {
      try {
        const response = await analyticsApi.getStockSummary({
          product_code: productCode,
          ...(departmentId ? { department_id: departmentId } : {}),
          ...selectionQuery(selectedClientIds, selectedWarehouseCodes),
        })
        if (!cancelled) {
          setSummary(response.data.data)
        }
      } catch (loadError) {
        if (!cancelled) {
          setSummary(null)
          message.error(getApiErrorMessage(loadError, 'Не удалось загрузить сводку'))
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [productCode, departmentId, selectedClientIds, selectedWarehouseCodes, selectionEmpty])

  useEffect(() => {
    if (!productCode || !dateFrom || !dateTo || selectionEmpty) {
      setSeries(null)
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    void (async () => {
      try {
        const response = await analyticsApi.getStockDynamics({
          product_code: productCode,
          date_from: dateFrom,
          date_to: dateTo,
          granularity,
          ...(departmentId ? { department_id: departmentId } : {}),
          ...selectionQuery(selectedClientIds, selectedWarehouseCodes),
        })
        if (!cancelled) {
          setSeries(response.data.data)
        }
      } catch (loadError) {
        if (!cancelled) {
          const text = getApiErrorMessage(loadError, 'Не удалось загрузить график')
          setError(text)
          setSeries(null)
          message.error(text)
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [
    productCode,
    departmentId,
    selectedClientIds,
    selectedWarehouseCodes,
    selectionEmpty,
    dateFrom,
    dateTo,
    granularity,
  ])

  const onGranularity = (value: StockGranularity) => {
    setRangeMode('auto')
    setGranularity(value)
    if (value === 'month') {
      setDateFrom('')
      setDateTo('')
      return
    }
    const range = defaultStockRange(value, dayjs())
    setDateFrom(range.from)
    setDateTo(range.to)
  }

  const onProduct = (code: number | undefined) => {
    setProductCode(code)
    setSelectedClientIds(null)
    setSelectedWarehouseCodes(null)
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={3} style={{ margin: 0 }}>
        Аналитика запасов
      </Typography.Title>
      <Card>
        <Space wrap size="middle" align="end">
          <div style={{ minWidth: 260 }}>
            <Typography.Text type="secondary">Продукт</Typography.Text>
            <ProductAutocomplete
              ariaLabel="Продукт"
              value={productCode}
              onChange={onProduct}
            />
          </div>
          <div style={{ minWidth: 240 }}>
            <Typography.Text type="secondary">Подразделение</Typography.Text>
            <Select
              allowClear
              showSearch
              aria-label="Подразделение"
              optionFilterProp="label"
              placeholder="Все подразделения"
              style={{ width: '100%' }}
              value={departmentId}
              onChange={(value) => setDepartmentId(value)}
              options={departments.map((item) => ({
                value: item.id,
                label: item.name,
              }))}
            />
          </div>
          <div>
            <Typography.Text type="secondary">Период</Typography.Text>
            <RangePicker
              aria-label="Период"
              allowClear={false}
              format="DD.MM.YYYY"
              value={
                dateFrom && dateTo
                  ? [dayjs(dateFrom), dayjs(dateTo)]
                  : null
              }
              onChange={(values: [Dayjs | null, Dayjs | null] | null) => {
                if (!values?.[0] || !values[1]) {
                  return
                }
                setRangeMode('manual')
                setDateFrom(values[0].format('YYYY-MM-DD'))
                setDateTo(values[1].format('YYYY-MM-DD'))
              }}
            />
          </div>
          <div style={{ minWidth: 140 }}>
            <Typography.Text type="secondary">Гранулярность</Typography.Text>
            <Select
              aria-label="Гранулярность"
              value={granularity}
              style={{ width: '100%' }}
              onChange={onGranularity}
              options={[
                { value: 'month', label: 'Месяц' },
                { value: 'week', label: 'Неделя' },
                { value: 'day', label: 'День' },
              ]}
            />
          </div>
          <Checkbox
            checked={showFullStock}
            onChange={(event) => setShowFullStock(event.target.checked)}
          >
            Показывать фактические остатки
          </Checkbox>
        </Space>
      </Card>
      {error ? <Alert type="error" message={error} /> : null}
      <Card>
        {!productCode ? (
          <Empty description="Выберите продукт" />
        ) : selectionEmpty ? (
          <Empty description="Выберите хотя бы один склад или клиента" />
        ) : (
          <Spin spinning={loading}>
            <StockDynamicsChart
              data={series}
              granularity={granularity}
              showFullStock={showFullStock}
            />
          </Spin>
        )}
      </Card>
      {productCode ? (
        <Card>
          <ShipmentSelectionTables
            clients={filterClients}
            warehouses={filterWarehouses}
            selectedClientIds={selectedClientIds}
            selectedWarehouseCodes={selectedWarehouseCodes}
            onClientsChange={setSelectedClientIds}
            onWarehousesChange={setSelectedWarehouseCodes}
          />
        </Card>
      ) : null}
      {productCode && !selectionEmpty ? (
        <Card title="Сводка за последние 6 месяцев">
          <StockSummaryTable data={summary} />
        </Card>
      ) : null}
    </Space>
  )
}
