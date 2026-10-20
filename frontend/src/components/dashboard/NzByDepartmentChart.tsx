import { Empty } from 'antd'
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
import type { DashboardMassUnit, NzByDepartmentData } from '../../api/types'
import { formatMass } from './formatMass'
import { rankWarehouseVolumes } from './warehouseTrendColors'

interface NzByDepartmentChartProps {
  data: NzByDepartmentData | null
  unit: DashboardMassUnit
}

export function axisWidthForLabels(labels: string[]): number {
  const longest = labels.reduce((best, label) => (label.length > best.length ? label : best), '')
  const fallback = longest.length * 12 + 28
  if (typeof document === 'undefined') {
    return fallback
  }
  try {
    const context = document.createElement('canvas').getContext('2d')
    if (!context) {
      return fallback
    }
    context.font = '12px sans-serif'
    const measured = context.measureText(longest).width
    if (!measured) {
      return fallback
    }
    return Math.ceil(measured) + 28
  } catch {
    return fallback
  }
}

function DepartmentTick({
  x = 0,
  y = 0,
  payload,
}: {
  x?: number
  y?: number
  payload?: { value?: string }
}) {
  return (
    <text x={x} y={y} dy={4} textAnchor="end" fill="rgba(0, 0, 0, 0.88)" fontSize={12}>
      {payload?.value}
    </text>
  )
}

export function NzByDepartmentChart({ data, unit }: NzByDepartmentChartProps) {
  if (!data || data.items.length === 0) {
    return <Empty description="Нет активных нормативов" />
  }
  const volumes = new Map<number, { name: string; volume: number }>()
  for (const item of data.items) {
    for (const warehouse of item.warehouses) {
      const current = volumes.get(warehouse.warehouse_code)
      volumes.set(warehouse.warehouse_code, {
        name: warehouse.warehouse_name,
        volume: (current?.volume ?? 0) + Number(warehouse.nz_quantity),
      })
    }
  }
  const legend = rankWarehouseVolumes(
    [...volumes.entries()].map(([warehouseCode, entry]) => ({
      warehouseCode,
      warehouseName: entry.name,
      volume: entry.volume,
    })),
  )
  const rows = data.items.map((item) => {
    const row: Record<string, string | number> = { department: item.department_name }
    for (const warehouse of item.warehouses) {
      row[`wh:${warehouse.warehouse_code}`] = Number(warehouse.nz_quantity)
    }
    return row
  })
  const labelWidth = axisWidthForLabels(rows.map((row) => String(row.department)))
  return (
    <div style={{ width: '100%', height: Math.max(rows.length * 48 + 48, 280) }}>
      <ResponsiveContainer>
        <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 16, top: 8, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" tickFormatter={(value: number) => formatMass(Number(value), unit)} />
          <YAxis
            type="category"
            dataKey="department"
            width={labelWidth}
            interval={0}
            tick={DepartmentTick}
          />
          <Tooltip formatter={(value) => [`${formatMass(Number(value), unit)} ${unit}`, 'НЗ']} />
          <Legend />
          {legend.map((warehouse) => (
            <Bar
              key={warehouse.warehouseCode}
              dataKey={`wh:${warehouse.warehouseCode}`}
              name={warehouse.warehouseName}
              stackId="nz"
              fill={warehouse.color}
              radius={2}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
