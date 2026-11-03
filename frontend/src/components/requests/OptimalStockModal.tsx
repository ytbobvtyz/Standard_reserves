import { Alert, Modal, Table, Typography } from 'antd'
import { Link } from 'react-router-dom'
import type {
  OptimalCalculatedItem,
  OptimalCalculateData,
  OptimalExistingNormative,
  OptimalSkippedItem,
} from '../../api/types'

interface OptimalStockModalProps {
  open: boolean
  loading: boolean
  result: OptimalCalculateData | null
  overwriteLabels: string[]
  onCancel: () => void
  onApply: () => void
}

interface Row {
  key: string
  product_code: number
  product_name: string
  warehouse_name: string
  quantity: number | null
  months: number | null
  reason: string | null
}

function formatDate(value: string): string {
  const [year, month, day] = value.slice(0, 10).split('-')
  if (!year || !month || !day) {
    return value
  }
  return `${day}.${month}.${year}`
}

function formatQty(value: number, unit: string): string {
  return `${value.toLocaleString('ru-RU', { maximumFractionDigits: 2 })} ${unit}`
}

function rowsOf(result: OptimalCalculateData | null): Row[] {
  if (!result) {
    return []
  }
  const calculated: Row[] = result.items.map((item: OptimalCalculatedItem) => ({
    key: `ok-${item.product_code}-${item.warehouse_code}`,
    product_code: item.product_code,
    product_name: item.product_name,
    warehouse_name: item.warehouse_name,
    quantity: item.calculated_quantity,
    months: item.months_used,
    reason: null,
  }))
  const skipped: Row[] = result.skipped_items.map((item: OptimalSkippedItem) => ({
    key: `skip-${item.product_code}-${item.warehouse_code}`,
    product_code: item.product_code,
    product_name: item.product_name,
    warehouse_name: item.warehouse_name,
    quantity: null,
    months: null,
    reason: item.reason,
  }))
  return [...calculated, ...skipped]
}

function normativeLabel(item: OptimalExistingNormative): string {
  const number = item.request_id ? item.request_id.slice(0, 8) : item.id.slice(0, 8)
  return `Запрос №${number} от ${formatDate(item.created_at)} — ${item.product_name} (${formatQty(item.quantity, item.unit)}, до ${formatDate(item.expiry_date)})`
}

export function OptimalStockModal({
  open,
  loading,
  result,
  overwriteLabels,
  onCancel,
  onApply,
}: OptimalStockModalProps) {
  return (
    <Modal
      title="🪄 Рассчитать оптимальный запас"
      open={open}
      onCancel={onCancel}
      okText="Применить"
      cancelText="Отмена"
      onOk={() => onApply()}
      okButtonProps={{ disabled: loading || result == null }}
      confirmLoading={loading}
      width={960}
      destroyOnHidden
    >
      <Typography.Paragraph>
        Клиент: {result?.client_name ?? '—'}
      </Typography.Paragraph>
      {overwriteLabels.length > 0 ? (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 12 }}
          message="Количество в уже добавленных строках будет перезаписано"
          description={overwriteLabels.join('; ')}
        />
      ) : null}
      <Typography.Title level={5}>Рассчитанные позиции</Typography.Title>
      <Table<Row>
        size="small"
        pagination={false}
        loading={loading}
        dataSource={rowsOf(result)}
        locale={{ emptyText: 'Нет позиций' }}
        columns={[
          { title: 'Артикул', dataIndex: 'product_code', width: 100 },
          { title: 'Название', dataIndex: 'product_name' },
          { title: 'Склад', dataIndex: 'warehouse_name', width: 160 },
          {
            title: 'Кол-во (кг/мес)',
            dataIndex: 'quantity',
            width: 140,
            render: (value: number | null) =>
              value == null
                ? '—'
                : value.toLocaleString('ru-RU', { maximumFractionDigits: 2 }),
          },
          {
            title: 'Месяцев',
            dataIndex: 'months',
            width: 90,
            render: (value: number | null) => (value == null ? '—' : value),
          },
          {
            title: 'Статус',
            width: 220,
            render: (_value, row) =>
              row.reason ? `⚠️ ${row.reason}` : '✅',
          },
        ]}
      />
      <Typography.Title level={5} style={{ marginTop: 16 }}>
        Действующие нормативы
      </Typography.Title>
      {result && result.existing_normatives.length > 0 ? (
        <ul>
          {result.existing_normatives.map((item) => (
            <li key={item.id}>
              {normativeLabel(item)}
              {item.request_id ? (
                <>
                  {' '}
                  —{' '}
                  <Link
                    to={`/requests/${item.request_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    открыть
                  </Link>
                </>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <Typography.Paragraph type="secondary">
          Действующих коммерческих нормативов нет
        </Typography.Paragraph>
      )}
    </Modal>
  )
}
