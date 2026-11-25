import { Checkbox, Table, Tag, Tooltip, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { ClientProductRow, ClientUnmatchedPoint, ClientWarehouseRow } from '../../api/types'
import {
  coverageLevel,
  formatCoverage,
  type CoverageThresholds,
} from '../../utils/coverage'
import { formatTons } from './stockDynamics'
import { sortClientRows, toggleCode } from './clientAnalytics'

function tons(value: number | null): string {
  if (value == null) {
    return '—'
  }
  return `${formatTons(value)} т`
}

function CoverageCell({
  months,
  thresholds,
}: {
  months: number | null
  thresholds: CoverageThresholds
}) {
  const level = coverageLevel(months, thresholds)
  const color =
    level === 'high' ? '#389e0d' : level === 'low' || level === 'none' ? '#cf1322' : undefined
  return <span style={{ color }}>{formatCoverage(months)}</span>
}

function NameCell({ name, outside }: { name: string; outside: boolean }) {
  return (
    <span style={{ display: 'inline-flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
      <span>{name}</span>
      {outside ? <Tag color="orange">Нет в нормативе</Tag> : null}
    </span>
  )
}

export function ClientCoverageTables({
  warehouses,
  products,
  unmatched,
  selectedWarehouses,
  selectedProducts,
  thresholds,
  onWarehousesChange,
  onProductsChange,
}: {
  warehouses: ClientWarehouseRow[]
  products: ClientProductRow[]
  unmatched: ClientUnmatchedPoint[]
  selectedWarehouses: number[] | null
  selectedProducts: number[] | null
  thresholds: CoverageThresholds
  onWarehousesChange: (codes: number[] | null) => void
  onProductsChange: (codes: number[] | null) => void
}) {
  const warehouseCodes = warehouses.map((item) => item.code)
  const productCodes = products.map((item) => item.code)
  const chosenWarehouses = selectedWarehouses ?? warehouseCodes
  const chosenProducts = selectedProducts ?? productCodes
  const warehouseSet = new Set(chosenWarehouses)
  const productSet = new Set(chosenProducts)
  const warehouseRows = sortClientRows(
    warehouses.map((item) => ({ ...item, label: item.name })),
  )
  const productRows = sortClientRows(
    products.map((item) => ({ ...item, label: `${item.code} ${item.name}` })),
  )

  const metricColumns = <T extends ClientWarehouseRow | ClientProductRow>(): ColumnsType<T> => [
    {
      title: 'Норматив сейчас',
      dataIndex: 'normative_tons',
      align: 'right',
      width: 140,
      sorter: (left, right) => left.normative_tons - right.normative_tons,
      render: (value: number) => tons(value),
    },
    {
      title: 'Среднемесячная',
      dataIndex: 'avg_monthly_tons',
      align: 'right',
      width: 150,
      sorter: (left, right) => (left.avg_monthly_tons ?? -1) - (right.avg_monthly_tons ?? -1),
      render: (value: number | null) => tons(value),
    },
    {
      title: 'За период',
      dataIndex: 'period_tons',
      align: 'right',
      width: 130,
      sorter: (left, right) => (left.period_tons ?? -1) - (right.period_tons ?? -1),
      render: (value: number | null) => tons(value),
    },
    {
      title: 'Покрытие',
      dataIndex: 'coverage_months',
      align: 'right',
      width: 140,
      sorter: (left, right) => (left.coverage_months ?? -1) - (right.coverage_months ?? -1),
      render: (value: number | null) => <CoverageCell months={value} thresholds={thresholds} />,
    },
  ]

  const warehouseColumns: ColumnsType<(typeof warehouseRows)[number]> = [
    {
      title: (
        <Checkbox
          aria-label="Все склады"
          disabled={warehouses.length === 0}
          checked={warehouses.length > 0 && chosenWarehouses.length === warehouses.length}
          indeterminate={
            chosenWarehouses.length > 0 && chosenWarehouses.length < warehouses.length
          }
          onChange={(event) => onWarehousesChange(event.target.checked ? null : [])}
        />
      ),
      width: 48,
      render: (_, row) => (
        <Checkbox
          aria-label={`Склад ${row.name}`}
          checked={warehouseSet.has(row.code)}
          onChange={(event) =>
            onWarehousesChange(
              toggleCode(selectedWarehouses, warehouseCodes, row.code, event.target.checked),
            )
          }
        />
      ),
    },
    {
      title: 'Склад',
      dataIndex: 'name',
      render: (_, row) => <NameCell name={row.name} outside={row.outside_normative} />,
    },
    ...metricColumns<(typeof warehouseRows)[number]>(),
  ]

  const productColumns: ColumnsType<(typeof productRows)[number]> = [
    {
      title: (
        <Checkbox
          aria-label="Все артикулы"
          disabled={products.length === 0}
          checked={products.length > 0 && chosenProducts.length === products.length}
          indeterminate={chosenProducts.length > 0 && chosenProducts.length < products.length}
          onChange={(event) => onProductsChange(event.target.checked ? null : [])}
        />
      ),
      width: 48,
      render: (_, row) => (
        <Checkbox
          aria-label={`Артикул ${row.code} ${row.name}`}
          checked={productSet.has(row.code)}
          onChange={(event) =>
            onProductsChange(
              toggleCode(selectedProducts, productCodes, row.code, event.target.checked),
            )
          }
        />
      ),
    },
    {
      title: 'Артикул',
      dataIndex: 'name',
      render: (_, row) => (
        <NameCell name={`${row.code} ${row.name}`} outside={row.outside_normative} />
      ),
    },
    {
      title: 'Норматив сейчас',
      dataIndex: 'normative_tons',
      align: 'right',
      width: 140,
      render: (value: number) => tons(value),
    },
    {
      title: 'Среднемесячная',
      dataIndex: 'avg_monthly_tons',
      align: 'right',
      width: 150,
      render: (value: number | null, row) => {
        const hasRelatedSales = row.related.some(
          (item) => item.avg_monthly_tons != null && item.avg_monthly_tons > 0,
        )
        const text = tons(value)
        if (row.related.length === 0) {
          return text
        }
        return (
          <Tooltip
            title={
              <div>
                {row.related.map((item) => (
                  <div key={item.code}>
                    {item.code} {item.name}: {tons(item.avg_monthly_tons)}
                  </div>
                ))}
              </div>
            }
          >
            <span
              style={
                hasRelatedSales
                  ? { background: '#fff1b8', padding: '0 4px' }
                  : undefined
              }
            >
              {text}
            </span>
          </Tooltip>
        )
      },
    },
    {
      title: 'За период',
      dataIndex: 'period_tons',
      align: 'right',
      width: 130,
      render: (value: number | null) => tons(value),
    },
    {
      title: 'Покрытие',
      dataIndex: 'coverage_months',
      align: 'right',
      width: 140,
      render: (value: number | null) => <CoverageCell months={value} thresholds={thresholds} />,
    },
  ]

  const unmatchedColumns: ColumnsType<ClientUnmatchedPoint> = [
    { title: 'Пункт отгрузки', dataIndex: 'loading_point' },
    {
      title: 'Среднемесячная',
      dataIndex: 'avg_monthly_tons',
      align: 'right',
      render: (value: number | null) => tons(value),
    },
    {
      title: 'За период',
      dataIndex: 'period_tons',
      align: 'right',
      render: (value: number | null) => tons(value),
    },
    {
      title: 'Покрытие',
      dataIndex: 'coverage_months',
      align: 'right',
      render: (value: number | null) => <CoverageCell months={value} thresholds={thresholds} />,
    },
  ]

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
      <div>
        <Typography.Text>
          Выбрано складов: {chosenWarehouses.length} из {warehouses.length}
        </Typography.Text>
        <Table
          size="small"
          pagination={false}
          rowKey="code"
          scroll={{ y: 360 }}
          dataSource={warehouseRows}
          columns={warehouseColumns}
          onRow={(row) => ({
            style: row.outside_normative ? { background: '#fff7e6' } : undefined,
          })}
        />
        {unmatched.length > 0 ? (
          <>
            <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>
              Пункты отгрузки без склада. В среднемесячную артикула они не входят. В график и
              итог среза попадают, пока отмечены все склады.
            </Typography.Paragraph>
            <Table
              size="small"
              pagination={false}
              rowKey="loading_point"
              dataSource={unmatched}
              columns={unmatchedColumns}
              onRow={() => ({ style: { background: '#fff7e6' } })}
            />
          </>
        ) : null}
      </div>
      <div>
        <Typography.Text>
          Выбрано артикулов: {chosenProducts.length} из {products.length}
        </Typography.Text>
        <Table
          size="small"
          pagination={false}
          rowKey="code"
          scroll={{ y: 360 }}
          dataSource={productRows}
          columns={productColumns}
          onRow={(row) => ({
            style: row.outside_normative ? { background: '#fff7e6' } : undefined,
          })}
        />
      </div>
    </div>
  )
}
