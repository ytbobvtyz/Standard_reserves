import { Table, Tag } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { DashboardExceptionItem, DashboardMassUnit } from '../../api/types'
import { formatMass } from './formatMass'

interface ExceptionsTableProps {
  items: DashboardExceptionItem[]
  loading?: boolean
  unit: DashboardMassUnit
  onRowClick: (item: DashboardExceptionItem) => void
}

export function ExceptionsTable({
  items,
  loading,
  unit,
  onRowClick,
}: ExceptionsTableProps) {
  const columns: ColumnsType<DashboardExceptionItem> = [
    { title: 'Артикул', dataIndex: 'product_code', width: 110 },
    { title: 'Название', dataIndex: 'product_name', ellipsis: true },
    { title: 'Склад', dataIndex: 'warehouse_name' },
    {
      title: `Норматив, ${unit}`,
      dataIndex: 'normative_quantity',
      render: (value: number) => formatMass(value, unit),
    },
    {
      title: `Доступно, ${unit}`,
      dataIndex: 'available',
      render: (value: number) => formatMass(value, unit),
    },
    {
      title: `Дефицит, ${unit}`,
      dataIndex: 'deficit',
      render: (value: number, row) => (
        <Tag color={row.status === 'critical' ? 'red' : 'gold'}>
          {formatMass(value, unit)}
        </Tag>
      ),
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      render: (value: DashboardExceptionItem['status']) =>
        value === 'critical' ? 'Критично' : 'Внимание',
    },
  ]

  return (
    <Table
      rowKey={(row) => `${row.warehouse_code}-${row.product_code}`}
      columns={columns}
      dataSource={items}
      loading={loading}
      pagination={false}
      size="small"
      onRow={(row) => ({
        onClick: () => onRowClick(row),
        style: { cursor: 'pointer' },
      })}
    />
  )
}
