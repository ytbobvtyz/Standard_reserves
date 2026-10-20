import { Alert, Modal, Statistic, Table, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { ClientUploadDepartmentPlan, ClientUploadPreview } from '../../api/types'

interface ClientUploadPreviewModalProps {
  preview: ClientUploadPreview | null
  fileName?: string
  confirming: boolean
  onCancel: () => void
  onConfirm: () => void
}

function clientsPhrase(count: number): string {
  const rest = Math.abs(count) % 100
  const last = rest % 10
  const word =
    rest >= 11 && rest <= 14
      ? 'клиентов'
      : last === 1
        ? 'клиент'
        : last >= 2 && last <= 4
          ? 'клиента'
          : 'клиентов'
  return `${count} ${word}`
}

const departmentColumns: ColumnsType<ClientUploadDepartmentPlan> = [
  { title: 'Подразделение', dataIndex: 'department_name' },
  { title: 'Будет создано', dataIndex: 'count', width: 140, align: 'right' },
]

export function ClientUploadPreviewModal({
  preview,
  fileName,
  confirming,
  onCancel,
  onConfirm,
}: ClientUploadPreviewModalProps) {
  const canUpload = (preview?.to_create ?? 0) > 0
  return (
    <Modal
      open={preview != null}
      title="Проверка перед загрузкой"
      width={720}
      okText={canUpload ? `Загрузить ${preview?.to_create}` : 'Нечего загружать'}
      cancelText="Отмена"
      confirmLoading={confirming}
      okButtonProps={{ disabled: !canUpload }}
      cancelButtonProps={{ disabled: confirming }}
      onOk={onConfirm}
      onCancel={onCancel}
      destroyOnHidden
    >
      {preview ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {fileName ? (
            <Typography.Text type="secondary">Файл: {fileName}</Typography.Text>
          ) : null}
          <Typography.Paragraph style={{ marginBottom: 0 }}>{preview.message}</Typography.Paragraph>
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
            <Statistic title="Будет создано" value={preview.to_create} />
            <Statistic title="Строк в файле" value={preview.file_rows} />
            <Statistic title="Ошибок" value={preview.errors} />
            <Statistic title="Без подразделения" value={preview.without_department} />
          </div>
          {preview.without_department > 0 ? (
            <Alert
              type="warning"
              showIcon
              message={
                preview.without_department === 1
                  ? '1 клиент будет создан без подразделения и попадёт в группу «Без управления».'
                  : `${clientsPhrase(preview.without_department)} будут созданы без подразделения и попадут в группу «Без управления».`
              }
            />
          ) : null}
          {preview.departments.length > 0 ? (
            <Table
              size="small"
              pagination={false}
              rowKey={(row) => row.department_id ?? 'none'}
              dataSource={preview.departments}
              columns={departmentColumns}
            />
          ) : null}
          {preview.errors > 0 ? (
            <Alert
              type="warning"
              showIcon
              message="Эти строки не будут загружены"
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
