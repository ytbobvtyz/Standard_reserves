import { Alert, Button, Modal, Table, Typography, Upload, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useState } from 'react'
import { getApiErrorMessage } from '../../api/client'
import { logisticsApi } from '../../api/logistics'
import type {
  AvailableBalancePreviewRow,
  BalancePreviewResult,
  BalanceUploadResult,
  MovingBalancePreviewRow,
} from '../../api/types'

interface BalanceUploadModalProps {
  open: boolean
  onClose: () => void
  onUploaded: () => Promise<void>
}

const availableColumns: ColumnsType<AvailableBalancePreviewRow> = [
  { title: 'Строка', dataIndex: 'row', width: 80 },
  { title: 'Артикул', dataIndex: 'product_code', width: 110 },
  { title: 'Завод', dataIndex: 'plant', width: 90 },
  { title: 'Склад', dataIndex: 'warehouse', width: 90 },
  { title: 'Запас', dataIndex: 'full_stock', width: 100 },
  { title: 'Доступно', dataIndex: 'available', width: 110 },
  { title: 'В пути', dataIndex: 'on_way', width: 100 },
]

const movingColumns: ColumnsType<MovingBalancePreviewRow> = [
  { title: 'Строка', dataIndex: 'row', width: 80 },
  { title: 'Артикул', dataIndex: 'product_code', width: 110 },
  { title: 'Склад', dataIndex: 'warehouse', width: 90 },
  { title: 'Статус', dataIndex: 'status', width: 90, render: (value?: string | null) => value || '—' },
  { title: 'Вес нетто', dataIndex: 'net_weight', width: 110 },
  { title: 'Открыто', dataIndex: 'opened', width: 100 },
  { title: 'Ед.', dataIndex: 'sales_unit', width: 70 },
  {
    title: 'Транспортный заказ',
    dataIndex: 'transport_order',
    render: (value?: string | null) => value || '—',
  },
]

function fileLabel(file?: string | null): string {
  return file === 'moving' ? 'Перемещения' : 'Доступные остатки'
}

export function BalanceUploadModal({ open, onClose, onUploaded }: BalanceUploadModalProps) {
  const [availableFile, setAvailableFile] = useState<File | null>(null)
  const [movingFile, setMovingFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<BalancePreviewResult | null>(null)
  const [checking, setChecking] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<BalanceUploadResult | null>(null)

  useEffect(() => {
    if (open) {
      return
    }
    setAvailableFile(null)
    setMovingFile(null)
    setPreview(null)
    setResult(null)
    setChecking(false)
    setUploading(false)
  }, [open])

  useEffect(() => {
    if (!open || !availableFile || !movingFile) {
      setPreview(null)
      return
    }
    let cancelled = false
    setChecking(true)
    setResult(null)
    void logisticsApi
      .previewBalances(availableFile, movingFile)
      .then(({ data }) => {
        if (!cancelled) {
          setPreview(data.data)
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setPreview(null)
          message.error(getApiErrorMessage(error, 'Не удалось проверить файлы'))
        }
      })
      .finally(() => {
        if (!cancelled) {
          setChecking(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [open, availableFile, movingFile])

  const handleUpload = async () => {
    if (!availableFile || !movingFile || !preview?.can_upload) {
      return
    }
    setUploading(true)
    try {
      const { data } = await logisticsApi.uploadBalances(availableFile, movingFile)
      setResult(data.data)
      message.success(data.data.message)
      await onUploaded()
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось загрузить остатки'))
    } finally {
      setUploading(false)
    }
  }

  const canUpload = Boolean(preview?.can_upload) && !checking && !uploading
  const uploaded = result !== null

  return (
    <Modal
      title="Загрузить актуальные остатки"
      open={open}
      width={1040}
      okText={uploaded ? 'Закрыть' : 'Загрузить'}
      cancelText="Отмена"
      cancelButtonProps={uploaded ? { style: { display: 'none' } } : undefined}
      confirmLoading={uploading}
      okButtonProps={{ disabled: uploaded ? false : !canUpload }}
      onOk={() => {
        if (uploaded) {
          onClose()
          return
        }
        void handleUpload()
      }}
      onCancel={onClose}
      destroyOnHidden
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div>
          <Typography.Text strong>Доступные остатки</Typography.Text>
          <Upload
            accept=".xlsx,.xls"
            maxCount={1}
            fileList={
              availableFile
                ? [{ uid: 'available', name: availableFile.name, status: 'done' }]
                : []
            }
            beforeUpload={(file) => {
              setAvailableFile(file)
              return false
            }}
            onRemove={() => {
              setAvailableFile(null)
            }}
            disabled={uploading}
          >
            <Button disabled={uploading} style={{ marginTop: 8 }}>
              Выбрать файл
            </Button>
          </Upload>
        </div>
        <div>
          <Typography.Text strong>Перемещения</Typography.Text>
          <Upload
            accept=".xlsx,.xls"
            maxCount={1}
            fileList={
              movingFile ? [{ uid: 'moving', name: movingFile.name, status: 'done' }] : []
            }
            beforeUpload={(file) => {
              setMovingFile(file)
              return false
            }}
            onRemove={() => {
              setMovingFile(null)
            }}
            disabled={uploading}
          >
            <Button disabled={uploading} style={{ marginTop: 8 }}>
              Выбрать файл
            </Button>
          </Upload>
        </div>
        <Typography.Text type="secondary">
          Нужны оба файла. «Загрузить» доступна, если нет ошибок. Неизвестный
          артикул пропускается и не блокирует остальные строки. «Доступно из
          запаса» может быть отрицательным.
        </Typography.Text>
        {checking ? <Typography.Text>Проверяем файлы…</Typography.Text> : null}
        {preview ? (
          <>
            <Alert
              type={
                preview.errors > 0
                  ? 'error'
                  : (preview.warnings ?? 0) > 0
                    ? 'warning'
                    : 'success'
              }
              showIcon
              message={preview.message}
            />
            <div>
              <Typography.Text strong>
                Доступные остатки — первые 10 строк ({preview.available_rows})
              </Typography.Text>
              <Table
                size="small"
                pagination={false}
                rowKey={(row) => `available-${row.row}`}
                dataSource={preview.available_preview}
                columns={availableColumns}
                scroll={{ x: 720 }}
                style={{ marginTop: 8 }}
              />
            </div>
            <div>
              <Typography.Text strong>
                Перемещения — первые 10 строк ({preview.moving_rows})
              </Typography.Text>
              <Table
                size="small"
                pagination={false}
                rowKey={(row) => `moving-${row.row}`}
                dataSource={preview.moving_preview}
                columns={movingColumns}
                scroll={{ x: 860 }}
                style={{ marginTop: 8 }}
              />
            </div>
            {preview.error_details.length > 0 ? (
              <Alert
                type="error"
                showIcon
                message="Ошибки"
                description={
                  <div style={{ maxHeight: 220, overflow: 'auto' }}>
                    {preview.error_details.map((item) => (
                      <div key={`${item.file ?? 'available'}-${item.row}-${item.message}`}>
                        {fileLabel(item.file)}, строка {item.row}: {item.message}
                      </div>
                    ))}
                  </div>
                }
              />
            ) : null}
            {(preview.warning_details?.length ?? 0) > 0 ? (
              <Alert
                type="warning"
                showIcon
                message="Предупреждения"
                description={
                  <div style={{ maxHeight: 220, overflow: 'auto' }}>
                    {preview.warning_details?.map((item) => (
                      <div key={`warn-${item.file ?? 'available'}-${item.row}-${item.message}`}>
                        {fileLabel(item.file)}, строка {item.row}: {item.message}
                      </div>
                    ))}
                  </div>
                }
              />
            ) : null}
          </>
        ) : null}
        {result ? (
          <Alert type="success" showIcon message={result.message} />
        ) : null}
      </div>
    </Modal>
  )
}
