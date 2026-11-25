import { Alert, Card, Checkbox, DatePicker, Empty, Select, Space, Spin, Typography } from 'antd'
import type { Dayjs } from 'dayjs'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { analyticsApi } from '../api/analytics'
import { getApiErrorMessage } from '../api/client'
import { referencesApi } from '../api/references'
import type { ClientAnalyticsData } from '../api/types'
import { ClientAutocomplete } from '../components/clients/ClientAutocomplete'
import { ClientConsumptionChart } from '../components/analytics/ClientConsumptionChart'
import { ClientCoverageTables } from '../components/analytics/ClientCoverageTables'
import { chartBlocked } from '../components/analytics/clientAnalytics'
import {
  defaultStockRange,
  formatTons,
  type StockGranularity,
} from '../components/analytics/stockDynamics'
import {
  DEFAULT_COVERAGE_THRESHOLDS,
  formatCoverage,
  type CoverageThresholds,
} from '../utils/coverage'

const { RangePicker } = DatePicker
const initialRange = defaultStockRange('month', dayjs())

function tons(value: number | null): string {
  if (value == null) {
    return 'нет реализации'
  }
  return `${formatTons(value)} т`
}

export function ClientAnalyticsPage() {
  const { clientId } = useParams()
  const navigate = useNavigate()
  const [granularity, setGranularity] = useState<StockGranularity>('month')
  const [dateFrom, setDateFrom] = useState(initialRange.from)
  const [dateTo, setDateTo] = useState(initialRange.to)
  const [includeRelated, setIncludeRelated] = useState(true)
  const [selectedWarehouses, setSelectedWarehouses] = useState<number[] | null>(null)
  const [selectedProducts, setSelectedProducts] = useState<number[] | null>(null)
  const [data, setData] = useState<ClientAnalyticsData | null>(null)
  const [thresholds, setThresholds] = useState<CoverageThresholds>(DEFAULT_COVERAGE_THRESHOLDS)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [seenClient, setSeenClient] = useState(clientId)

  if (seenClient !== clientId) {
    const range = defaultStockRange('month', dayjs())
    setSeenClient(clientId)
    setSelectedWarehouses(null)
    setSelectedProducts(null)
    setData(null)
    setError(null)
    setGranularity('month')
    setDateFrom(range.from)
    setDateTo(range.to)
  }

  useEffect(() => {
    let cancelled = false
    void referencesApi
      .getParams()
      .then(({ data: response }) => {
        if (!cancelled) {
          setThresholds({
            highMonths: Number(response.data.coverage_high_months),
            lowMonths: Number(response.data.coverage_low_months),
          })
        }
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
    if (!data) {
      return
    }
    const warehouseCodes = new Set(data.warehouses.map((item) => item.code))
    const productCodes = new Set(data.products.map((item) => item.code))
    if (selectedWarehouses !== null) {
      const next = selectedWarehouses.filter((code) => warehouseCodes.has(code))
      if (next.length !== selectedWarehouses.length) {
        setSelectedWarehouses(next.length === data.warehouses.length ? null : next)
      }
    }
    if (selectedProducts !== null) {
      const next = selectedProducts.filter((code) => productCodes.has(code))
      if (next.length !== selectedProducts.length) {
        setSelectedProducts(next.length === data.products.length ? null : next)
      }
    }
  }, [data, selectedProducts, selectedWarehouses])

  useEffect(() => {
    if (!clientId || !dateFrom || !dateTo) {
      setData(null)
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    void (async () => {
      try {
        const response = await analyticsApi.getClientAnalytics(clientId, {
          date_from: dateFrom,
          date_to: dateTo,
          granularity,
          include_related: includeRelated,
          ...(selectedWarehouses !== null ? { warehouse_codes: selectedWarehouses } : {}),
          ...(selectedProducts !== null ? { product_codes: selectedProducts } : {}),
        })
        if (!cancelled) {
          setData(response.data.data)
        }
      } catch (loadError) {
        if (!cancelled) {
          setData(null)
          setError(getApiErrorMessage(loadError, 'Не удалось загрузить аналитику клиента'))
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
    clientId,
    dateFrom,
    dateTo,
    granularity,
    includeRelated,
    selectedProducts,
    selectedWarehouses,
  ])

  const onGranularity = (value: StockGranularity) => {
    setGranularity(value)
    const range = defaultStockRange(value, dayjs())
    setDateFrom(range.from)
    setDateTo(range.to)
  }

  const warehouseTotal = data?.warehouses.length ?? 0
  const productTotal = data?.products.length ?? 0
  const blocked = chartBlocked(
    warehouseTotal,
    selectedWarehouses,
    productTotal,
    selectedProducts,
  )
  const noRows =
    data !== null &&
    data.warehouses.length === 0 &&
    data.products.length === 0 &&
    data.unmatched.length === 0

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={3} style={{ margin: 0 }}>
        Аналитика по клиенту
      </Typography.Title>
      <Card>
        <Space wrap size="middle" align="end">
          <div style={{ minWidth: 280 }}>
            <Typography.Text type="secondary">Клиент</Typography.Text>
            <ClientAutocomplete
              ariaLabel="Клиент"
              value={clientId}
              onChange={(id) => {
                navigate(id ? `/analytics/client/${id}` : '/analytics/client')
              }}
            />
          </div>
          <div>
            <Typography.Text type="secondary">Период</Typography.Text>
            <RangePicker
              aria-label="Период"
              allowClear={false}
              format="DD.MM.YYYY"
              value={dateFrom && dateTo ? [dayjs(dateFrom), dayjs(dateTo)] : null}
              onChange={(values: [Dayjs | null, Dayjs | null] | null) => {
                if (!values?.[0] || !values[1]) {
                  return
                }
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
            checked={includeRelated}
            onChange={(event) => setIncludeRelated(event.target.checked)}
          >
            Учитывать родственные артикулы в покрытии
          </Checkbox>
        </Space>
        <Typography.Paragraph type="secondary" style={{ marginTop: 12, marginBottom: 0 }}>
          {data?.department_name
            ? `Управление продаж: ${data.department_name}. `
            : ''}
          Среднемесячная — 6 полных месяцев до текущего, как в согласовании экономиста.
          Переключатель добавляет продажи родственников в покрытие артикула и итог среза.
          Строка склада уже включает все отгрузки клиента с этого склада.
        </Typography.Paragraph>
      </Card>

      {!clientId ? <Empty description="Выберите клиента" /> : null}
      {clientId && data?.is_system ? (
        <Alert
          type="info"
          showIcon
          message="Служебная карточка «Общий клиент». Нормативы, заведённые до справочника клиентов, собраны здесь."
        />
      ) : null}
      {error ? <Alert type="error" showIcon message={error} /> : null}

      {clientId && data && !noRows ? (
        <Card>
          {blocked ? (
            <Empty description="Отметьте хотя бы один склад и один артикул" />
          ) : (
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <Typography.Text strong>Срез отмеченных складов и артикулов</Typography.Text>
              <Space size="large" wrap>
                <span>Норматив сейчас: {formatTons(data.slice.normative_tons)} т</span>
                <span>Среднемесячная: {tons(data.slice.avg_monthly_tons)}</span>
                <span>Покрытие: {formatCoverage(data.slice.coverage_months)}</span>
                <span>
                  Реализация за период:{' '}
                  {data.slice.period_tons == null ? '—' : `${formatTons(data.slice.period_tons)} т`}
                </span>
              </Space>
              {data.slice.outside_normative ? (
                <TagNotice />
              ) : null}
              <Spin spinning={loading}>
                <ClientConsumptionChart data={data.chart} granularity={granularity} />
              </Spin>
            </Space>
          )}
        </Card>
      ) : null}

      {clientId && noRows && !loading ? (
        <Empty description="По клиенту нет нормативов и реализации за период" />
      ) : null}

      {clientId && data && !noRows ? (
        <Card>
          <Typography.Paragraph type="secondary">
            Сверху потребление без норматива, затем норматив без реализации, затем самое
            большое покрытие.
          </Typography.Paragraph>
          <ClientCoverageTables
            warehouses={data.warehouses}
            products={data.products}
            unmatched={data.unmatched}
            selectedWarehouses={selectedWarehouses}
            selectedProducts={selectedProducts}
            thresholds={thresholds}
            onWarehousesChange={setSelectedWarehouses}
            onProductsChange={setSelectedProducts}
          />
        </Card>
      ) : null}
      {clientId && loading && !data ? <Spin /> : null}
    </Space>
  )
}

function TagNotice() {
  return (
    <Typography.Text style={{ color: '#d46b08' }}>
      В срезе есть потребление, которого нет в нормативе клиента.
    </Typography.Text>
  )
}
