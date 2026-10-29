import { Table } from 'antd'
import type { StockMonthSummary, StockSummaryData } from '../../api/types'
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

export function averageColumn(
  months: StockMonthSummary[],
  key: 'available_median' | 'actual' | 'normative_avg',
): number | null {
  const present = months
    .map((month) => month[key])
    .filter((value): value is number => value != null)
  if (present.length === 0) {
    return null
  }
  return present.reduce((sum, value) => sum + value, 0) / present.length
}

export function StockSummaryTable({ data }: StockSummaryTableProps) {
  if (!data) {
    return null
  }
  const averageMedian = averageColumn(data.months, 'available_median')
  const averageActual = averageColumn(data.months, 'actual')
  const averageNormative = averageColumn(data.months, 'normative_avg')
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
        summary={() => (
          <Table.Summary.Row>
            <Table.Summary.Cell index={0}>Среднее</Table.Summary.Cell>
            <Table.Summary.Cell index={1} align="right">
              {formatCell(averageMedian)}
            </Table.Summary.Cell>
            <Table.Summary.Cell index={2} align="right">
              {formatCell(averageActual)}
            </Table.Summary.Cell>
            <Table.Summary.Cell index={3} align="right">
              {formatCell(averageNormative)}
            </Table.Summary.Cell>
          </Table.Summary.Row>
        )}
      />
    </div>
  )
}
