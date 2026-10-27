import { Button, DatePicker, Space, Table, Typography, message } from 'antd'
import { DownloadOutlined, UploadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useState } from 'react'
import { actualShipmentsApi } from '../api/actualShipments'
import { getApiErrorMessage } from '../api/client'
import type { ActualShipmentListItem, ActualShipmentUploadResult, UserRole } from '../api/types'
import { ClientAutocomplete } from '../components/clients/ClientAutocomplete'
import { ProductAutocomplete } from '../components/requests/ProductAutocomplete'
import { ActualShipmentUploadModal } from '../components/shipments/ActualShipmentUploadModal'
import { useAuthStore } from '../stores/auth'
import { downloadBlob } from '../utils/download'

const UPLOAD_ROLES: UserRole[] = ['logistics', 'economist', 'pp']

interface FilterState {
  client_id?: string
  product_code?: number
  date_from?: string
  date_to?: string
}

function formatShipmentDate(value: string): string {
  const [year, month, day] = value.slice(0, 10).split('-')
  if (!year || !month || !day) {
    return value
  }
  return `${day}.${month}.${year}`
}

export function ActualShipmentsPage() {
  const user = useAuthStore((state) => state.user)
  const canUpload = user != null && UPLOAD_ROLES.includes(user.role)
  const [draft, setDraft] = useState<FilterState>({})
  const [applied, setApplied] = useState<FilterState>({})
  const [items, setItems] = useState<ActualShipmentListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [preview, setPreview] = useState<ActualShipmentUploadResult | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [parsing, setParsing] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [pickerKey, setPickerKey] = useState(0)
  const limit = 20

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await actualShipmentsApi.list({
        ...applied,
        page,
        limit,
      })
      setItems(data.data)
      setTotal(data.meta?.total ?? data.data.length)
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось загрузить реализацию'))
    } finally {
      setLoading(false)
    }
  }, [applied, page])

  useEffect(() => {
    void load()
  }, [load])

  const applyFilters = () => {
    setPage(1)
    setApplied({ ...draft })
  }

  const resetFilters = () => {
    setDraft({})
    setApplied({})
    setPage(1)
    setPickerKey((current) => current + 1)
  }

  const closeUpload = () => {
    if (confirming) {
      return
    }
    setUploadOpen(false)
    setPreview(null)
    setFile(null)
    setParsing(false)
  }

  const handleFile = async (next: File) => {
    const name = next.name.toLowerCase()
    if (!name.endsWith('.xlsx') && !name.endsWith('.xls')) {
      message.error('Загрузите файл .xlsx или .xls')
      return
    }
    setFile(next)
    setPreview(null)
    setParsing(true)
    try {
      const { data } = await actualShipmentsApi.upload(next, false)
      setPreview(data.data)
    } catch (error) {
      setFile(null)
      message.error(getApiErrorMessage(error, 'Не удалось прочитать файл'))
    } finally {
      setParsing(false)
    }
  }

  const handleConfirm = async () => {
    if (!file || !preview || preview.valid_rows === 0) {
      return
    }
    setConfirming(true)
    try {
      const { data } = await actualShipmentsApi.upload(file, true)
      if (data.data.inserted > 0) {
        message.success(data.data.message)
      } else {
        message.warning(data.data.message)
      }
      setUploadOpen(false)
      setPreview(null)
      setFile(null)
      await load()
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось сохранить реализацию'))
    } finally {
      setConfirming(false)
    }
  }

  const handleTemplate = async () => {
    setDownloading(true)
    try {
      const { data } = await actualShipmentsApi.downloadTemplate()
      downloadBlob(data, 'actual-shipments-template.xlsx')
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось скачать шаблон'))
    } finally {
      setDownloading(false)
    }
  }

  const columns: ColumnsType<ActualShipmentListItem> = [
    {
      title: 'Клиент',
      render: (_value, row) => `${row.client_code} — ${row.client_name}`,
    },
    {
      title: 'Артикул',
      render: (_value, row) => `${row.product_code} — ${row.product_name}`,
    },
    { title: 'Количество', dataIndex: 'quantity', width: 130 },
    { title: 'Единица', dataIndex: 'unit', width: 100 },
    {
      title: 'Дата отгрузки',
      dataIndex: 'shipment_date',
      width: 150,
      render: (value: string) => formatShipmentDate(value),
    },
    {
      title: '№ накладной',
      dataIndex: 'invoice_number',
      width: 150,
      render: (value?: string | null) => value || '—',
    },
    {
      title: 'Маршрут',
      dataIndex: 'route',
      render: (value?: string | null) => value || '—',
    },
  ]

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={3} style={{ margin: 0 }}>
        Продажи
      </Typography.Title>
      <Typography.Text type="secondary">Фактическая реализация</Typography.Text>
      <Space wrap>
        <div data-testid="client-filter" style={{ width: 280 }}>
          <ClientAutocomplete
            ariaLabel="Клиент"
            value={draft.client_id}
            onChange={(clientId) =>
              setDraft((current) => ({ ...current, client_id: clientId }))
            }
          />
        </div>
        <div data-testid="product-filter" style={{ width: 280 }}>
          <ProductAutocomplete
            ariaLabel="Артикул"
            value={draft.product_code}
            onChange={(productCode) =>
              setDraft((current) => ({ ...current, product_code: productCode }))
            }
          />
        </div>
        <DatePicker.RangePicker
          key={pickerKey}
          aria-label="Дата отгрузки"
          format="DD.MM.YYYY"
          placeholder={['Дата с', 'Дата по']}
          allowClear
          onChange={(values) =>
            setDraft((current) => ({
              ...current,
              date_from: values?.[0]?.format('YYYY-MM-DD'),
              date_to: values?.[1]?.format('YYYY-MM-DD'),
            }))
          }
        />
        <Button type="primary" onClick={applyFilters}>
          Применить фильтр
        </Button>
        <Button onClick={resetFilters}>Сбросить</Button>
        {canUpload ? (
          <Button
            icon={<DownloadOutlined />}
            loading={downloading}
            onClick={() => void handleTemplate()}
          >
            Выгрузить шаблон
          </Button>
        ) : null}
        {canUpload ? (
          <Button
            icon={<UploadOutlined />}
            onClick={() => {
              setPreview(null)
              setFile(null)
              setUploadOpen(true)
            }}
          >
            Загрузить из Excel
          </Button>
        ) : null}
      </Space>
      <Table
        rowKey="id"
        loading={loading}
        columns={columns}
        dataSource={items}
        pagination={{
          current: page,
          pageSize: limit,
          total,
          showSizeChanger: false,
          onChange: (next) => setPage(next),
        }}
        locale={{ emptyText: 'Отгрузок не найдено' }}
        scroll={{ x: 900 }}
      />
      <ActualShipmentUploadModal
        open={uploadOpen}
        preview={preview}
        fileName={file?.name}
        loading={parsing}
        confirming={confirming}
        onCancel={closeUpload}
        onConfirm={() => void handleConfirm()}
        onFile={(next) => void handleFile(next)}
      />
    </Space>
  )
}
