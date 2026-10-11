import { Alert, Empty } from 'antd'
import {
  Bar,
  BarChart,
  Brush,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { DashboardTrendData, DashboardTrendSeries } from '../../api/types'
import {
  colorForSeries,
  rankWarehouses,
  type WarehouseLegendEntry,
} from './warehouseTrendColors'

interface NormativeTrendChartProps {
  data: DashboardTrendData | null
  selectedPeriod: string | null
  onPeriodClick: (period: string) => void
}

function formatPeriod(value: string, groupBy: DashboardTrendData['group_by']): string {
  const date = new Date(`${value}T00:00:00`)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  if (groupBy === 'month') {
    return date.toLocaleDateString('ru-RU', { month: 'short', year: 'numeric' })
  }
  return date.toLocaleDateString('ru-RU')
}

function seriesName(series: DashboardTrendSeries): string {
  if (series.product_name === 'Остальные') {
    return 'Остальные'
  }
  if (series.product_name) {
    return `${series.warehouse_name} · ${series.product_name}`
  }
  return series.warehouse_name
}

function TrendLegend({ entries }: { entries: WarehouseLegendEntry[] }) {
  const top = entries.filter((item) => item.rank < 3)
  const rest = entries.filter((item) => item.rank >= 3)
  const group = (title: string, items: WarehouseLegendEntry[]) => (
    <div key={title} style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
      <span style={{ fontWeight: 600 }}>{title}</span>
      {items.map((item) => (
        <span key={item.warehouseCode} style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
          <span
            style={{
              width: 12,
              height: 12,
              borderRadius: 2,
              background: item.color,
              display: 'inline-block',
            }}
          />
          {item.warehouseName}
        </span>
      ))}
    </div>
  )
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, paddingTop: 8 }}>
      {group('Топ-3', top)}
      {rest.length > 0 ? group('Остальные склады', rest) : null}
    </div>
  )
}

export function NormativeTrendChart({
  data,
  selectedPeriod,
  onPeriodClick,
}: NormativeTrendChartProps) {
  if (!data || data.series.length === 0) {
    return <Empty description="Нет данных для графика" />
  }

  const chartRows = data.periods.map((period) => {
    const row: Record<string, string | number> = { period }
    for (const series of data.series) {
      const point = series.points.find((item) => item.period === period)
      row[series.key] = point?.total_normative ?? 0
    }
    return row
  })
  const legend = rankWarehouses(data.series, data.periods)
  const colorByWarehouse = new Map(legend.map((item) => [item.warehouseCode, item.rank]))
  const orderedSeries = [...data.series].sort((left, right) => {
    const leftRank = colorByWarehouse.get(left.warehouse_code) ?? Number.MAX_SAFE_INTEGER
    const rightRank = colorByWarehouse.get(right.warehouse_code) ?? Number.MAX_SAFE_INTEGER
    return leftRank - rightRank
  })
  const chartWidth = Math.max(data.periods.length * 64, 560)

  return (
    <>
      {selectedPeriod ? (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12 }}
          message={`Фильтр по дате: ${formatPeriod(selectedPeriod, data.group_by)}`}
        />
      ) : null}
      <div className="trend-chart-scroll">
        <div style={{ width: chartWidth, minWidth: '100%', height: 380 }}>
          <ResponsiveContainer>
            <BarChart
              data={chartRows}
              onClick={(state) => {
                const label = state?.activeLabel
                if (typeof label === 'string') {
                  onPeriodClick(label)
                }
              }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="period"
                tickFormatter={(value: string) => formatPeriod(value, data.group_by)}
              />
              <YAxis
                tickFormatter={(value: number) => String(value)}
                label={{ value: data.unit, angle: -90, position: 'insideLeft' }}
              />
              <Tooltip
                labelFormatter={(value) =>
                  formatPeriod(String(value), data.group_by)
                }
                formatter={(value) => [`${value} ${data.unit}`, undefined]}
              />
              <Legend content={() => <TrendLegend entries={legend} />} />
              {orderedSeries.map((series) => (
                <Bar
                  key={series.key}
                  dataKey={series.key}
                  name={seriesName(series)}
                  stackId="normative"
                  fill={colorForSeries(series, legend)}
                  cursor="pointer"
                />
              ))}
              {data.periods.length > 8 ? (
                <Brush dataKey="period" height={22} travellerWidth={8} />
              ) : null}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </>
  )
}
