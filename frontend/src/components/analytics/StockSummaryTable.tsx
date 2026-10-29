import { Table } from 'antd'
import type { StockSummaryData } from '../../api/types'
import { formatStockPeriod, formatTons } from './stockDynamics'

interface StockSummaryTableProps {
  data: StockSummaryData | null
}

function formatCell(value: number | null): string {
  if (value == null) {
    return '—'
  }
  return formatTons(value)
}

export function StockSummaryTable({ data }: StockSummaryTableProps) {
  if (!data) {
    return null
  }
  return (
    <div data-testid="stock-summary">
      <Table
        size="small"
        pagination={false}
        rowKey="month"
        dataSource={data.months}
        columns={[
          {
            title: 'Месяц',
            dataIndex: 'month',
            render: (value: string) => formatStockPeriod(value, 'month'),
          },
          {
            title: `Медианный остаток, ${data.unit}`,
            dataIndex: 'available_median',
            align: 'right',
            render: (value: number | null) => formatCell(value),
          },
          {
            title: `Реализация, ${data.unit}`,
            dataIndex: 'actual',
            align: 'right',
            render: (value: number | null) => formatCell(value),
          },
          {
            title: `Средний норматив, ${data.unit}`,
            dataIndex: 'normative_avg',
            align: 'right',
            render: (value: number | null) => formatCell(value),
          },
        ]}
      />
    </div>
  )
}
