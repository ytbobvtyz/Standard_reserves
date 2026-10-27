import { Empty, Typography } from 'antd'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { DashboardMassUnit, WarehouseCoverageData } from '../../api/types'
import { formatMass } from './formatMass'

interface WarehouseCoverageChartProps {
  data: WarehouseCoverageData | null
  unit: DashboardMassUnit
}

export function WarehouseCoverageChart({ data, unit }: WarehouseCoverageChartProps) {
  if (!data || data.warehouses.length === 0) {
    return <Empty description="Нет данных по складам" />
  }

  const chartWidth = Math.max(data.warehouses.length * 120, 560)
  const rows = data.warehouses.map((item) => ({
    warehouse: item.warehouse_name,
    available: item.available,
    planned: item.planned,
    deficit: item.deficit,
    normative: item.normative_quantity,
  }))

  return (
    <>
      <div className="trend-chart-scroll">
        <div style={{ width: chartWidth, minWidth: '100%', height: 380 }}>
          <ResponsiveContainer>
            <BarChart data={rows}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="warehouse" interval={0} angle={-25} textAnchor="end" height={70} />
              <YAxis
                tickFormatter={(value: number) => formatMass(Number(value), unit)}
                label={{ value: unit, angle: -90, position: 'insideLeft' }}
              />
              <Tooltip
                formatter={(value) => [
                  `${formatMass(Number(value), unit)} ${unit}`,
                  undefined,
                ]}
              />
              <Legend />
              <Bar dataKey="available" name="Доступно" stackId="cover" fill="#52c41a" />
              <Bar
                dataKey="planned"
                name="Запланировано"
                stackId="cover"
                fill="#faad14"
              />
              <Bar dataKey="deficit" name="Дефицит" stackId="cover" fill="#ff4d4f" />
              <Bar dataKey="normative" name="Нормативный запас" fill="#1677ff" radius={2} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <Typography.Paragraph type="secondary" style={{ marginTop: 12, marginBottom: 0 }}>
        Без фильтра по подразделению и клиенту «доступно» и «запланировано» — те же
        суммы, что в шапке склада на странице логистики (все остатки). Если подразделение
        или клиент выбраны, в расчёт входят только артикулы из нормативов этого отбора.
        «Запланировано» = plan − доступно, не ниже нуля. Красный блок — дефицит по этим
        позициям, синий прямоугольник — нормативный запас. Покрытие = (норматив − сумма
        дефицитов) / норматив; если все позиции покрыты, это 100%.
      </Typography.Paragraph>
    </>
  )
}
