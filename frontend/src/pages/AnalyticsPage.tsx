import { Alert, Card, DatePicker, Empty, Select, Space, Spin, Typography, message } from 'antd'
import type { Dayjs } from 'dayjs'
import dayjs from 'dayjs'
import { useCallback, useEffect, useState } from 'react'
import { analyticsApi } from '../api/analytics'
import { getApiErrorMessage } from '../api/client'
import { referencesApi } from '../api/references'
import type {
  DepartmentListItem,
  ObjectListItem,
  StockDynamicsData,
  StockSummaryData,
} from '../api/types'
import { ClientAutocomplete } from '../components/clients/ClientAutocomplete'
import { StockDynamicsChart } from '../components/analytics/StockDynamicsChart'
import { StockSummaryTable } from '../components/analytics/StockSummaryTable'
import {
  defaultStockRange,
  type StockGranularity,
} from '../components/analytics/stockDynamics'
import { ProductAutocomplete } from '../components/requests/ProductAutocomplete'

const { RangePicker } = DatePicker

export function AnalyticsPage() {
  const [productCode, setProductCode] = useState<number | undefined>()
  const [warehouseCode, setWarehouseCode] = useState<number | undefined>()
  const [departmentId, setDepartmentId] = useState<string | undefined>()
  const [clientId, setClientId] = useState<string | undefined>()
  const [granularity, setGranularity] = useState<StockGranularity>('month')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [rangeMode, setRangeMode] = useState<'auto' | 'manual'>('auto')
  const [warehouses, setWarehouses] = useState<ObjectListItem[]>([])
  const [departments, setDepartments] = useState<DepartmentListItem[]>([])
  const [series, setSeries] = useState<StockDynamicsData | null>(null)
  const [summary, setSummary] = useState<StockSummaryData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const [objectsResp, departmentsResp] = await Promise.all([
          referencesApi.getObjects({ type: 'warehouse', is_active: true, limit: 200 }),
          referencesApi.getDepartments({ has_normatives: true }),
        ])
        if (cancelled) {
          return
        }
        setWarehouses(objectsResp.data.data)
        setDepartments(departmentsResp.data.data)
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
    if (granularity !== 'month' || rangeMode !== 'auto') {
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
          ...(warehouseCode ? { warehouse_code: warehouseCode } : {}),
          ...(departmentId ? { department_id: departmentId } : {}),
          ...(clientId ? { client_id: clientId } : {}),
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
  }, [granularity, rangeMode, productCode, warehouseCode, departmentId, clientId])

  useEffect(() => {
    if (!productCode) {
      setSummary(null)
      return
    }
    let cancelled = false
    void (async () => {
      try {
        const response = await analyticsApi.getStockSummary({
          product_code: productCode,
          ...(warehouseCode ? { warehouse_code: warehouseCode } : {}),
          ...(departmentId ? { department_id: departmentId } : {}),
          ...(clientId ? { client_id: clientId } : {}),
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
  }, [productCode, warehouseCode, departmentId, clientId])

  const loadSeries = useCallback(async () => {
    if (!productCode || !dateFrom || !dateTo) {
      setSeries(null)
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const response = await analyticsApi.getStockDynamics({
        product_code: productCode,
        date_from: dateFrom,
        date_to: dateTo,
        granularity,
        ...(warehouseCode ? { warehouse_code: warehouseCode } : {}),
        ...(departmentId ? { department_id: departmentId } : {}),
        ...(clientId ? { client_id: clientId } : {}),
      })
      setSeries(response.data.data)
    } catch (loadError) {
      const text = getApiErrorMessage(loadError, 'Не удалось загрузить график')
      setError(text)
      setSeries(null)
      message.error(text)
    } finally {
      setLoading(false)
    }
  }, [
    productCode,
    warehouseCode,
    departmentId,
    clientId,
    dateFrom,
    dateTo,
    granularity,
  ])

  useEffect(() => {
    void loadSeries()
  }, [loadSeries])

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
              onChange={(code) => setProductCode(code)}
            />
          </div>
          <div style={{ minWidth: 220 }}>
            <Typography.Text type="secondary">Склад</Typography.Text>
            <Select
              allowClear
              showSearch
              aria-label="Склад"
              optionFilterProp="label"
              placeholder="Все склады"
              style={{ width: '100%' }}
              value={warehouseCode}
              onChange={(value) => setWarehouseCode(value)}
              options={warehouses.map((item) => ({
                value: item.code,
                label: `${item.code} · ${item.name}`,
              }))}
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
          <div style={{ minWidth: 260 }}>
            <Typography.Text type="secondary">Клиент</Typography.Text>
            <ClientAutocomplete
              ariaLabel="Клиент"
              value={clientId}
              onChange={(id) => setClientId(id)}
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
        </Space>
      </Card>
      {error ? <Alert type="error" message={error} /> : null}
      <Card>
        {!productCode ? (
          <Empty description="Выберите продукт" />
        ) : (
          <Spin spinning={loading}>
            <StockDynamicsChart data={series} granularity={granularity} />
          </Spin>
        )}
      </Card>
      {productCode ? (
        <Card title="Сводка за последние 6 месяцев">
          <StockSummaryTable data={summary} />
        </Card>
      ) : null}
    </Space>
  )
}
