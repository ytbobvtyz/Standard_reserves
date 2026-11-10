import { Checkbox, Table, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { AnalyticsFilterClient, AnalyticsFilterWarehouse } from '../../api/types'

interface ShipmentSelectionTablesProps {
  clients: AnalyticsFilterClient[]
  warehouses: AnalyticsFilterWarehouse[]
  selectedClientIds: string[] | null
  selectedWarehouseCodes: number[] | null
  onClientsChange: (ids: string[] | null) => void
  onWarehousesChange: (codes: number[] | null) => void
}

function formatKg(value: number): string {
  return new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

function nextIds(
  current: string[] | null,
  all: string[],
  id: string,
  checked: boolean,
): string[] | null {
  const selected = new Set(current ?? all)
  if (checked) {
    selected.add(id)
  } else {
    selected.delete(id)
  }
  if (selected.size === all.length) {
    return null
  }
  return all.filter((item) => selected.has(item))
}

function nextCodes(
  current: number[] | null,
  all: number[],
  code: number,
  checked: boolean,
): number[] | null {
  const selected = new Set(current ?? all)
  if (checked) {
    selected.add(code)
  } else {
    selected.delete(code)
  }
  if (selected.size === all.length) {
    return null
  }
  return all.filter((item) => selected.has(item))
}

export function ShipmentSelectionTables({
  clients,
  warehouses,
  selectedClientIds,
  selectedWarehouseCodes,
  onClientsChange,
  onWarehousesChange,
}: ShipmentSelectionTablesProps) {
  const clientIds = clients.map((item) => item.id)
  const warehouseCodes = warehouses.map((item) => item.code)
  const chosenClients = selectedClientIds ?? clientIds
  const chosenWarehouses = selectedWarehouseCodes ?? warehouseCodes
  const clientSet = new Set(chosenClients)
  const warehouseSet = new Set(chosenWarehouses)

  const clientColumns: ColumnsType<AnalyticsFilterClient> = [
    {
      title: (
        <Checkbox
          aria-label="Все клиенты"
          disabled={clients.length === 0}
          checked={clients.length > 0 && chosenClients.length === clients.length}
          indeterminate={
            chosenClients.length > 0 && chosenClients.length < clients.length
          }
          onChange={(event) => onClientsChange(event.target.checked ? null : [])}
        />
      ),
      width: 48,
      render: (_, row) => (
        <Checkbox
          aria-label={`Клиент ${row.name}`}
          checked={clientSet.has(row.id)}
          onChange={(event) =>
            onClientsChange(nextIds(selectedClientIds, clientIds, row.id, event.target.checked))
          }
        />
      ),
    },
    { title: 'Клиент', dataIndex: 'name' },
    {
      title: 'Отгрузки, кг',
      dataIndex: 'shipment_kg',
      align: 'right',
      width: 140,
      render: (value: number) => formatKg(value),
    },
  ]

  const warehouseColumns: ColumnsType<AnalyticsFilterWarehouse> = [
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
              nextCodes(selectedWarehouseCodes, warehouseCodes, row.code, event.target.checked),
            )
          }
        />
      ),
    },
    { title: 'Склад', dataIndex: 'name' },
    {
      title: 'Отгрузки, кг',
      dataIndex: 'shipment_kg',
      align: 'right',
      width: 140,
      render: (value: number) => formatKg(value),
    },
  ]

  return (
    <div>
      <Typography.Text data-testid="selection-counter">
        {`Выбрано: ${chosenClients.length} из ${clients.length} клиентов, ${chosenWarehouses.length} из ${warehouses.length} складов`}
      </Typography.Text>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: 16,
          marginTop: 12,
        }}
      >
        <Table
          size="small"
          pagination={false}
          rowKey="id"
          data-testid="client-filter-table"
          columns={clientColumns}
          dataSource={clients}
          scroll={{ y: 280 }}
          locale={{ emptyText: 'Нет отгрузок за 6 месяцев' }}
        />
        <Table
          size="small"
          pagination={false}
          rowKey="code"
          data-testid="warehouse-filter-table"
          columns={warehouseColumns}
          dataSource={warehouses}
          scroll={{ y: 280 }}
          locale={{ emptyText: 'Нет отгрузок за 6 месяцев' }}
        />
      </div>
    </div>
  )
}
