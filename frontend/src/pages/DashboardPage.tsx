import {
  Card,
  DatePicker,
  Radio,
  Select,
  Space,
  Spin,
  Typography,
  Alert,
  Table,
  message,
} from 'antd'
import type { Dayjs } from 'dayjs'
import dayjs from 'dayjs'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { dashboardApi } from '../api/dashboard'
import { referencesApi } from '../api/references'
import { getApiErrorMessage } from '../api/client'
import { ClientAutocomplete } from '../components/clients/ClientAutocomplete'
import { ProductAutocomplete } from '../components/requests/ProductAutocomplete'
import type {
  DashboardExceptionItem,
  DashboardGroupBy,
  DashboardMassUnit,
  DashboardSummary,
  DashboardTrendData,
  DepartmentListItem,
  ExpiryCalendarData,
  NzByDepartmentData,
  ObjectListItem,
  TopClientsData,
  WarehouseCoverageData,
} from '../api/types'
import { NorthStarRow } from '../components/dashboard/NorthStarRow'
import { NormativeTrendChart } from '../components/dashboard/NormativeTrendChart'
import { WarehouseCoverageChart } from '../components/dashboard/WarehouseCoverageChart'
import { ExceptionsTable } from '../components/dashboard/ExceptionsTable'
import { ExpiryHeatmap } from '../components/dashboard/ExpiryHeatmap'
import { NzByDepartmentChart } from '../components/dashboard/NzByDepartmentChart'
import { TopClientsChart } from '../components/dashboard/TopClientsChart'
import { formatMass } from '../components/dashboard/formatMass'

const EXCEPTIONS_LIMIT = 20

export function DashboardPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [trend, setTrend] = useState<DashboardTrendData | null>(null)
  const [exceptions, setExceptions] = useState<DashboardExceptionItem[]>([])
  const [exceptionsTotal, setExceptionsTotal] = useState(0)
  const [coverage, setCoverage] = useState<WarehouseCoverageData | null>(null)
  const [calendar, setCalendar] = useState<ExpiryCalendarData | null>(null)
  const [nzByDepartment, setNzByDepartment] = useState<NzByDepartmentData | null>(null)
  const [topClients, setTopClients] = useState<TopClientsData | null>(null)
  const [warehouses, setWarehouses] = useState<ObjectListItem[]>([])
  const [departments, setDepartments] = useState<DepartmentListItem[]>([])
  const [productCode, setProductCode] = useState<number | undefined>()
  const [clientId, setClientId] = useState<string | undefined>()
  const [warehouseCode, setWarehouseCode] = useState<number | undefined>()
  const [departmentId, setDepartmentId] = useState<string | undefined>()
  const [groupBy, setGroupBy] = useState<DashboardGroupBy>('week')
  const [dateFrom, setDateFrom] = useState<string | undefined>()
  const [dateTo, setDateTo] = useState<string | undefined>()
  const [unit, setUnit] = useState<DashboardMassUnit>('т')
  const [selectedPeriod, setSelectedPeriod] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loadFilters = useCallback(async () => {
    const [objectsResp, departmentsResp] = await Promise.all([
      referencesApi.getObjects({ type: 'warehouse', is_active: true, limit: 200 }),
      referencesApi.getDepartments({ has_normatives: true }),
    ])
    setWarehouses(objectsResp.data.data)
    setDepartments(departmentsResp.data.data)
  }, [])

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    setError(null)
    const scope = {
      ...(warehouseCode ? { warehouse_code: warehouseCode } : {}),
      ...(departmentId ? { department_id: departmentId } : {}),
    }
    try {
      const [
        summaryResp,
        trendResp,
        exceptionsResp,
        coverageResp,
        calendarResp,
        nzResp,
        topResp,
      ] = await Promise.all([
        dashboardApi.getSummary({ unit, ...scope }),
        dashboardApi.getNormativeTrend({
          product_code: productCode,
          client_id: clientId,
          group_by: groupBy,
          date_from: dateFrom,
          date_to: dateTo,
          unit,
          ...scope,
        }),
        dashboardApi.getExceptions({
          limit: EXCEPTIONS_LIMIT,
          unit,
          ...scope,
        }),
        dashboardApi.getWarehouseCoverage({ unit, ...scope }),
        dashboardApi.getExpiryCalendar({ unit, ...scope }),
        dashboardApi.getNzByDepartment({ unit, ...scope }),
        dashboardApi.getTopClients({ unit, limit: 10, ...scope }),
      ])
      setSummary(summaryResp.data.data)
      setTrend(trendResp.data.data)
      setExceptions(exceptionsResp.data.data)
      setExceptionsTotal(exceptionsResp.data.meta?.total ?? exceptionsResp.data.data.length)
      setCoverage(coverageResp.data.data)
      setCalendar(calendarResp.data.data)
      setNzByDepartment(nzResp.data.data)
      setTopClients(topResp.data.data)
    } catch (loadError) {
      const text = getApiErrorMessage(loadError, 'Не удалось загрузить дашборд')
      setError(text)
      message.error(text)
    } finally {
      setLoading(false)
    }
  }, [productCode, clientId, warehouseCode, departmentId, groupBy, dateFrom, dateTo, unit])

  useEffect(() => {
    void loadFilters()
  }, [loadFilters])

  useEffect(() => {
    void loadDashboard()
  }, [loadDashboard])

  const massUnit = summary?.unit ?? unit
  const hiddenExceptions = Math.max(exceptionsTotal - exceptions.length, 0)

  const drillRows = useMemo(() => {
    if (!trend || !selectedPeriod) {
      return []
    }
    return trend.series
      .map((series) => {
        const point = series.points.find((item) => item.period === selectedPeriod)
        return {
          key: series.key,
          warehouse_name: series.warehouse_name,
          product_name: series.product_name ?? 'Все артикулы',
          total_normative: point?.total_normative ?? 0,
          count_active: point?.count_active ?? 0,
        }
      })
      .filter((row) => row.total_normative > 0 || row.count_active > 0)
  }, [trend, selectedPeriod])

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Space align="center" wrap style={{ width: '100%', justifyContent: 'space-between' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>
          Дашборд нормативов
        </Typography.Title>
        <Space wrap>
          <div data-testid="warehouse-filter">
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="Склад"
              style={{ minWidth: 220 }}
              value={warehouseCode}
              onChange={(value) => {
                setSelectedPeriod(null)
                setWarehouseCode(value)
              }}
              options={warehouses.map((item) => ({
                value: item.code,
                label: `${item.code} · ${item.name}`,
              }))}
            />
          </div>
          <div data-testid="department-filter">
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="Все подразделения"
              style={{ minWidth: 240 }}
              value={departmentId}
              onChange={(value) => {
                setSelectedPeriod(null)
                setDepartmentId(value)
              }}
              options={departments.map((item) => ({
                value: item.id,
                label: item.name,
              }))}
            />
          </div>
          <Radio.Group
            optionType="button"
            buttonStyle="solid"
            value={unit}
            onChange={(event) => setUnit(event.target.value)}
            options={[
              { label: 'т', value: 'т' },
              { label: 'кг', value: 'кг' },
            ]}
          />
        </Space>
      </Space>
      {error ? <Alert type="error" message={error} /> : null}
      <Spin spinning={loading}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <NorthStarRow
            activeQuantity={summary?.active_quantity ?? 0}
            deficitQuantity={summary?.deficit_quantity ?? 0}
            coverageWithTransfers={summary?.coverage_with_transfers ?? 0}
            coverageAvailableOnly={summary?.coverage_available_only ?? 0}
            expiring30dQuantity={summary?.expiring_30d_quantity ?? 0}
            unit={massUnit}
          />

          <Card
            title="Динамика нормативов"
            extra={
              <Space wrap>
                <div data-testid="product-filter" style={{ minWidth: 240 }}>
                  <ProductAutocomplete
                    value={productCode}
                    onChange={(code) => {
                      setSelectedPeriod(null)
                      setProductCode(code)
                    }}
                  />
                </div>
                <div data-testid="client-filter" style={{ minWidth: 260 }}>
                  <ClientAutocomplete
                    value={clientId}
                    onChange={(id) => {
                      setSelectedPeriod(null)
                      setClientId(id)
                    }}
                  />
                </div>
                <DatePicker
                  placeholder="От"
                  allowClear
                  value={dateFrom ? dayjs(dateFrom) : null}
                  onChange={(value: Dayjs | null) => {
                    setSelectedPeriod(null)
                    setDateFrom(value ? value.format('YYYY-MM-DD') : undefined)
                  }}
                />
                <DatePicker
                  placeholder="До"
                  allowClear
                  value={dateTo ? dayjs(dateTo) : null}
                  onChange={(value: Dayjs | null) => {
                    setSelectedPeriod(null)
                    setDateTo(value ? value.format('YYYY-MM-DD') : undefined)
                  }}
                />
                <div data-testid="period-select">
                  <Select
                    aria-label="Период"
                    value={groupBy}
                    style={{ minWidth: 140 }}
                    onChange={(value) => {
                      setSelectedPeriod(null)
                      setGroupBy(value)
                    }}
                    options={[
                      { value: 'day', label: 'День' },
                      { value: 'week', label: 'Неделя' },
                      { value: 'month', label: 'Месяц' },
                    ]}
                  />
                </div>
              </Space>
            }
          >
            <NormativeTrendChart
              data={trend}
              selectedPeriod={selectedPeriod}
              onPeriodClick={(period) =>
                setSelectedPeriod((current) => (current === period ? null : period))
              }
            />
            {selectedPeriod ? (
              <Table
                style={{ marginTop: 16 }}
                size="small"
                pagination={false}
                rowKey="key"
                dataSource={drillRows}
                columns={[
                  { title: 'Склад', dataIndex: 'warehouse_name' },
                  { title: 'Артикул', dataIndex: 'product_name' },
                  {
                    title: `Норматив, ${trend?.unit ?? massUnit}`,
                    dataIndex: 'total_normative',
                    render: (value: number) => formatMass(value, trend?.unit ?? massUnit),
                  },
                  { title: 'НЗ', dataIndex: 'count_active' },
                ]}
              />
            ) : null}
          </Card>

          <Card title="НЗ в разрезе управлений продаж">
            <NzByDepartmentChart data={nzByDepartment} unit={massUnit} />
          </Card>

          <Card title="Топ-10 клиентов по объёму НЗ">
            <TopClientsChart data={topClients} unit={massUnit} />
          </Card>

          <Card title="Текущее покрытие по складам">
            <WarehouseCoverageChart data={coverage} unit={massUnit} />
          </Card>

          <Card title="Требуют внимания">
            <ExceptionsTable
              items={exceptions}
              loading={loading}
              unit={massUnit}
              onRowClick={(item) => {
                if (item.request_id) {
                  navigate(`/requests/${item.request_id}`)
                  return
                }
                navigate('/logistics/dashboard')
              }}
            />
            {hiddenExceptions > 0 ? (
              <Typography.Paragraph type="secondary" style={{ margin: '12px 0 0' }}>
                Показаны {exceptions.length} позиций с наибольшим дефицитом, ещё{' '}
                {hiddenExceptions} скрыто.
              </Typography.Paragraph>
            ) : null}
          </Card>

          <Card title="Календарь истечений">
            <ExpiryHeatmap data={calendar} />
          </Card>
        </Space>
      </Spin>
    </Space>
  )
}
