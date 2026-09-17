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

const COLORS = [
  '#1677ff',
  '#52c41a',
  '#fa8c16',
  '#722ed1',
  '#13c2c2',
  '#eb2f96',
  '#faad14',
  '#2f54eb',
  '#a0d911',
  '#8c8c8c',
]

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

function seriesColor(series: DashboardTrendSeries, index: number): string {
  if (series.product_name === 'Остальные' || series.key.includes(':other:')) {
    return '#8c8c8c'
  }
  return COLORS[index % COLORS.length]
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
              <Legend />
              {data.series.map((series, index) => (
                <Bar
                  key={series.key}
                  dataKey={series.key}
                  name={seriesName(series)}
                  stackId="normative"
                  fill={seriesColor(series, index)}
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
