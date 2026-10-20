import { Empty } from 'antd'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { DashboardMassUnit, TopClientItem, TopClientsData } from '../../api/types'
import { formatMass } from './formatMass'

export const OTHERS_BAR_COLOR = '#9CA3AF'
const CLIENT_BAR_COLOR = '#13c2c2'

interface TopClientsChartProps {
  data: TopClientsData | null
  unit: DashboardMassUnit
}

export function chartRowsForTopClients(items: TopClientItem[]) {
  const clients = items.filter((item) => !item.is_other)
  const others = items.find((item) => item.is_other)
  const ordered = [...clients].reverse()
  if (others) {
    ordered.unshift(others)
  }
  return ordered.map((item) => ({
    client: item.is_other ? item.client_name : `${item.client_code} · ${item.client_name}`,
    nz: Number(item.nz_quantity),
    isOther: Boolean(item.is_other),
  }))
}

export function TopClientsChart({ data, unit }: TopClientsChartProps) {
  if (!data || data.items.length === 0) {
    return <Empty description="Нет активных нормативов" />
  }
  const rows = chartRowsForTopClients(data.items)
  return (
    <div style={{ width: '100%', height: Math.max(rows.length * 36, 280) }}>
      <ResponsiveContainer>
        <BarChart data={rows} layout="vertical" margin={{ left: 24, right: 16 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" tickFormatter={(value: number) => formatMass(Number(value), unit)} />
          <YAxis type="category" dataKey="client" width={220} interval={0} />
          <Tooltip formatter={(value) => [`${formatMass(Number(value), unit)} ${unit}`, 'НЗ']} />
          <Bar dataKey="nz" name="НЗ" radius={2}>
            {rows.map((row) => (
              <Cell
                key={row.client}
                fill={row.isOther ? OTHERS_BAR_COLOR : CLIENT_BAR_COLOR}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
