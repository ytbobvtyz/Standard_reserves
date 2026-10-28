import { Alert, Modal, Progress, Table, Typography, Upload } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { ActualShipmentPreviewRow, ActualShipmentUploadResult } from '../../api/types'

interface ActualShipmentUploadModalProps {
  open: boolean
  preview: ActualShipmentUploadResult | null
  fileName?: string
  loading: boolean
  confirming: boolean
  onCancel: () => void
  onConfirm: () => void
  onFile: (file: File) => void
}

function formatShipmentDate(value: string): string {
  const [year, month, day] = value.slice(0, 10).split('-')
  if (!year || !month || !day) {
    return value
  }
  return `${day}.${month}.${year}`
}

const columns: ColumnsType<ActualShipmentPreviewRow> = [
  { title: 'Строка', dataIndex: 'row', width: 80 },
  {
    title: 'Клиент',
    render: (_value, row) => `${row.client_code} — ${row.client_name}`,
  },
  {
    title: 'Артикул',
    render: (_value, row) => `${row.product_code} — ${row.product_name}`,
  },
  { title: 'Вес нетто, кг', dataIndex: 'quantity', width: 130 },
  { title: 'Пункт отгрузки', dataIndex: 'loading_point', width: 140 },
  {
    title: 'Дата фактического ОМ',
    dataIndex: 'shipment_date',
    width: 170,
    render: (value: string) => formatShipmentDate(value),
  },
  {
    title: 'Транспортный заказ',
    dataIndex: 'invoice_number',
    width: 160,
    render: (value?: string | null) => value || '—',
  },
  {
    title: 'Маршрут',
    dataIndex: 'route',
    render: (value?: string | null) => value || '—',
  },
]

export function ActualShipmentUploadModal({
  open,
  preview,
  fileName,
  loading,
  confirming,
  onCancel,
  onConfirm,
  onFile,
}: ActualShipmentUploadModalProps) {
  const canSave = (preview?.valid_rows ?? 0) > 0
  return (
    <Modal
      open={open}
      title="Загрузить реализацию из Excel"
      width={960}
      okText="Сохранить"
      cancelText="Отмена"
      confirmLoading={confirming}
      okButtonProps={{ disabled: !canSave || loading }}
      cancelButtonProps={{ disabled: confirming }}
      onOk={onConfirm}
      onCancel={onCancel}
      destroyOnHidden
    >
      <Upload.Dragger
        accept=".xlsx,.xls"
        maxCount={1}
        showUploadList={false}
        disabled={loading || confirming}
        beforeUpload={(file) => {
          onFile(file)
          return false
        }}
      >
        <p>Перетащите Excel-файл сюда или нажмите, чтобы выбрать</p>
        <p>.xlsx или .xls. Сначала проверка, сохранение — после «Сохранить».</p>
      </Upload.Dragger>
      {loading ? <Progress percent={50} status="active" style={{ marginTop: 16 }} /> : null}
      {preview ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 16 }}>
          {fileName ? <Typography.Text type="secondary">Файл: {fileName}</Typography.Text> : null}
          <Typography.Paragraph style={{ marginBottom: 0 }}>{preview.message}</Typography.Paragraph>
          {preview.preview.length > 0 ? (
            <Table
              size="small"
              pagination={false}
              rowKey={(row) => String(row.row)}
              dataSource={preview.preview}
              columns={columns}
              scroll={{ x: 860, y: 280 }}
            />
          ) : null}
          {preview.missing_clients.length > 0 ? (
            <Alert
              type="info"
              showIcon
              message="Клиенты отсутствуют в справочнике, их строки не загружаются"
              description={
                <div style={{ maxHeight: 160, overflow: 'auto' }}>
                  {preview.missing_clients.map((item) => (
                    <div key={item.client_code}>
                      {item.client_code}
                      {item.client_name ? ` — ${item.client_name}` : ''}: {item.rows}
                    </div>
                  ))}
                </div>
              }
            />
          ) : null}
          {preview.missing_products.length > 0 ? (
            <Alert
              type="info"
              showIcon
              message="Продукты отсутствуют в справочнике, их строки не загружаются"
              description={
                <div style={{ maxHeight: 160, overflow: 'auto' }}>
                  {preview.missing_products.map((item) => (
                    <div key={item.product_code}>
                      {item.product_code}
                      {item.product_name ? ` — ${item.product_name}` : ''}: {item.rows}
                    </div>
                  ))}
                </div>
              }
            />
          ) : null}
          {preview.errors > 0 ? (
            <Alert
              type="warning"
              showIcon
              message="Эти строки не будут сохранены"
              description={
                <div style={{ maxHeight: 180, overflow: 'auto' }}>
                  {preview.error_details.map((item) => (
                    <div key={`${item.row}-${item.message}`}>
                      Строка {item.row}: {item.message}
                    </div>
                  ))}
                </div>
              }
            />
          ) : null}
        </div>
      ) : null}
    </Modal>
  )
}
