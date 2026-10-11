import { Empty } from 'antd'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { DashboardMassUnit, TopClientsData } from '../../api/types'
import { formatMass } from './formatMass'

interface TopClientsChartProps {
  data: TopClientsData | null
  unit: DashboardMassUnit
}

export function TopClientsChart({ data, unit }: TopClientsChartProps) {
  if (!data || data.items.length === 0) {
    return <Empty description="Нет активных нормативов" />
  }
  const rows = [...data.items]
    .reverse()
    .map((item) => ({
      client: `${item.client_code} · ${item.client_name}`,
      nz: Number(item.nz_quantity),
    }))
  return (
    <div style={{ width: '100%', height: Math.max(rows.length * 36, 280) }}>
      <ResponsiveContainer>
        <BarChart data={rows} layout="vertical" margin={{ left: 24, right: 16 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" tickFormatter={(value: number) => formatMass(Number(value), unit)} />
          <YAxis type="category" dataKey="client" width={220} />
          <Tooltip formatter={(value) => [`${formatMass(Number(value), unit)} ${unit}`, 'НЗ']} />
          <Bar dataKey="nz" name="НЗ" fill="#13c2c2" radius={2} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
