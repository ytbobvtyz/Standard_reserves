import { Empty } from 'antd'
import {
  Bar,
  Brush,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { ClientAnalyticsChart } from '../../api/types'
import {
  STOCK_ACTUAL_COLOR,
  STOCK_NORMATIVE_COLOR,
  formatStockPeriod,
  formatTons,
  type StockGranularity,
} from './stockDynamics'
import { clientChartHasData } from './clientAnalytics'

export function ClientConsumptionChart({
  data,
  granularity,
}: {
  data: ClientAnalyticsChart
  granularity: StockGranularity
}) {
  if (!clientChartHasData(data.normative, data.actual)) {
    return <Empty description="Нет данных за период" />
  }
  const rows = data.dates.map((date, index) => ({
    date,
    normative: data.normative[index] ?? null,
    actual: data.actual[index] ?? null,
  }))
  const showNormative = data.normative.some((value) => value != null)
  const showActual = data.actual.some((value) => value != null)
  const chartWidth = Math.max(rows.length * 48, 560)

  return (
    <>
      <div className="trend-chart-scroll">
        <div style={{ width: chartWidth, minWidth: '100%', height: 380 }}>
          <ResponsiveContainer>
            <ComposedChart data={rows}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tickFormatter={(value: string) => formatStockPeriod(value, granularity)}
              />
              <YAxis
                tickFormatter={(value: number) => formatTons(value)}
                label={{ value: data.unit, angle: -90, position: 'insideLeft' }}
              />
              <Tooltip
                labelFormatter={(value) => formatStockPeriod(String(value), granularity)}
                formatter={(value, name) => [
                  value == null ? '—' : `${formatTons(Number(value))} ${data.unit}`,
                  name,
                ]}
              />
              {showNormative ? (
                <Bar
                  dataKey="normative"
                  name="Норматив"
                  fill={STOCK_NORMATIVE_COLOR}
                  isAnimationActive={false}
                />
              ) : null}
              {showActual ? (
                <Line
                  type="monotone"
                  dataKey="actual"
                  name="Реализация"
                  stroke={STOCK_ACTUAL_COLOR}
                  strokeWidth={2}
                  connectNulls={false}
                  dot
                  isAnimationActive={false}
                />
              ) : null}
              {rows.length > 12 ? (
                <Brush dataKey="date" height={22} travellerWidth={8} />
              ) : null}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 16, paddingTop: 8 }}>
        {showNormative ? <span>Норматив</span> : null}
        {showActual ? <span>Реализация</span> : null}
      </div>
    </>
  )
}
