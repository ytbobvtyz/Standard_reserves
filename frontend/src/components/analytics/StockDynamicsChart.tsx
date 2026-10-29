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
import type { StockDynamicsData } from '../../api/types'
import {
  STOCK_ACTUAL_COLOR,
  STOCK_AVAILABLE_COLOR,
  STOCK_AVAILABLE_MAX_COLOR,
  STOCK_AVAILABLE_MIN_COLOR,
  STOCK_NORMATIVE_COLOR,
  buildStockChartModel,
  formatStockPeriod,
  formatTons,
  type StockGranularity,
} from './stockDynamics'

interface StockDynamicsChartProps {
  data: StockDynamicsData | null
  granularity: StockGranularity
}

function LegendItem({
  color,
  label,
  kind,
}: {
  color: string
  label: string
  kind: 'bar' | 'solid' | 'dashed'
}) {
  const swatch =
    kind === 'bar'
      ? { width: 12, height: 12, background: color }
      : kind === 'dashed'
        ? { width: 16, height: 0, borderTop: `3px dashed ${color}` }
        : { width: 16, height: 3, background: color }
  return (
    <span style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
      <span style={{ ...swatch, display: 'inline-block' }} />
      {label}
    </span>
  )
}

export function StockDynamicsChart({ data, granularity }: StockDynamicsChartProps) {
  if (!data) {
    return null
  }
  const model = buildStockChartModel(data)
  if (!model.hasNormative) {
    return <Empty description="Нет данных за период" />
  }
  const levelLabel = granularity === 'day' ? 'Доступный запас' : 'Медиана остатка'
  const chartWidth = Math.max(model.rows.length * 48, 560)

  return (
    <>
      <div className="trend-chart-scroll">
        <div style={{ width: chartWidth, minWidth: '100%', height: 380 }}>
          <ResponsiveContainer>
            <ComposedChart data={model.rows}>
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
              <Bar
                dataKey="normative"
                name="Норматив"
                fill={STOCK_NORMATIVE_COLOR}
                isAnimationActive={false}
              />
              {model.showAvailableMin ? (
                <Line
                  type="monotone"
                  dataKey="availableMin"
                  name="Мин. остаток"
                  stroke={STOCK_AVAILABLE_MIN_COLOR}
                  strokeWidth={2}
                  strokeDasharray="4 4"
                  connectNulls={false}
                  dot={false}
                  isAnimationActive={false}
                />
              ) : null}
              {model.showAvailableMax ? (
                <Line
                  type="monotone"
                  dataKey="availableMax"
                  name="Макс. остаток"
                  stroke={STOCK_AVAILABLE_MAX_COLOR}
                  strokeWidth={2}
                  strokeDasharray="4 4"
                  connectNulls={false}
                  dot={false}
                  isAnimationActive={false}
                />
              ) : null}
              {model.showAvailableLevel ? (
                <Line
                  type="monotone"
                  dataKey="availableMedian"
                  name={levelLabel}
                  stroke={STOCK_AVAILABLE_COLOR}
                  strokeWidth={2}
                  connectNulls={false}
                  dot
                  isAnimationActive={false}
                />
              ) : null}
              {model.showActual ? (
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
              {model.rows.length > 12 ? (
                <Brush dataKey="date" height={22} travellerWidth={8} />
              ) : null}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div
        data-testid="stock-legend"
        style={{ display: 'flex', flexWrap: 'wrap', gap: 16, paddingTop: 8 }}
      >
        <LegendItem color={STOCK_NORMATIVE_COLOR} label="Норматив" kind="bar" />
        {model.showAvailableMin ? (
          <LegendItem color={STOCK_AVAILABLE_MIN_COLOR} label="Мин. остаток" kind="dashed" />
        ) : null}
        {model.showAvailableLevel ? (
          <LegendItem color={STOCK_AVAILABLE_COLOR} label={levelLabel} kind="solid" />
        ) : null}
        {model.showAvailableMax ? (
          <LegendItem color={STOCK_AVAILABLE_MAX_COLOR} label="Макс. остаток" kind="dashed" />
        ) : null}
        {model.showActual ? (
          <LegendItem color={STOCK_ACTUAL_COLOR} label="Реализация" kind="solid" />
        ) : null}
      </div>
    </>
  )
}
