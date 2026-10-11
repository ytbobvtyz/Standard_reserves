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
import type { DashboardMassUnit, NzByDepartmentData } from '../../api/types'
import { formatMass } from './formatMass'

interface NzByDepartmentChartProps {
  data: NzByDepartmentData | null
  unit: DashboardMassUnit
}

export function NzByDepartmentChart({ data, unit }: NzByDepartmentChartProps) {
  if (!data || data.items.length === 0) {
    return <Empty description="Нет активных нормативов" />
  }
  const rows = data.items.map((item) => ({
    department: item.department_name,
    nz: Number(item.nz_quantity),
  }))
  const chartWidth = Math.max(rows.length * 140, 560)
  return (
    <div className="trend-chart-scroll">
      <div style={{ width: chartWidth, minWidth: '100%', height: 360 }}>
        <ResponsiveContainer>
          <BarChart data={rows}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="department" interval={0} angle={-25} textAnchor="end" height={80} />
            <YAxis tickFormatter={(value: number) => formatMass(Number(value), unit)} />
            <Tooltip formatter={(value) => [`${formatMass(Number(value), unit)} ${unit}`, 'НЗ']} />
            <Bar dataKey="nz" name="НЗ" fill="#1677ff" radius={2} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
