import {
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  UploadOutlined,
} from '@ant-design/icons'
import {
  Alert,
  Button,
  DatePicker,
  Form,
  Input,
  Modal,
  Popconfirm,
  Space,
  Table,
  Tag,
  Upload,
  Typography,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { UploadFile } from 'antd/es/upload/interface'
import type { Dayjs } from 'dayjs'
import dayjs from 'dayjs'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { getApiErrorMessage } from '../../api/client'
import { productionRequestsApi } from '../../api/productionRequests'
import type {
  ProductionRequestListItem,
  ProductionRequestUploadResult,
} from '../../api/types'
import { downloadBlob } from '../../utils/download'

const { RangePicker } = DatePicker

interface UploadValues {
  client_name?: string
  dates: [Dayjs, Dayjs]
}

interface DatesValues {
  dates: [Dayjs, Dayjs]
}

interface ProductionRequestsTabProps {
  onNormativesChanged: () => void
}

export function ProductionRequestsTab({
  onNormativesChanged,
}: ProductionRequestsTabProps) {
  const [uploadForm] = Form.useForm<UploadValues>()
  const [datesForm] = Form.useForm<DatesValues>()
  const [items, setItems] = useState<ProductionRequestListItem[]>([])
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [datesOpen, setDatesOpen] = useState(false)
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [uploadResult, setUploadResult] =
    useState<ProductionRequestUploadResult>()
  const [selectedId, setSelectedId] = useState<string>()

  const selected = useMemo(
    () => items.find((item) => item.id === selectedId),
    [items, selectedId],
  )

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await productionRequestsApi.list({ limit: 200 })
      setItems(data.data)
      if (selectedId && !data.data.some((item) => item.id === selectedId)) {
        setSelectedId(undefined)
      }
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось загрузить партии'))
    } finally {
      setLoading(false)
    }
  }, [selectedId])

  useEffect(() => {
    void load()
  }, [load])

  const openUpload = () => {
    uploadForm.setFieldsValue({
      client_name: undefined,
      dates: [dayjs(), dayjs().add(3, 'month')],
    })
    setFileList([])
    setUploadResult(undefined)
    setUploadOpen(true)
  }

  const submitUpload = async () => {
    const values = await uploadForm.validateFields()
    const file = fileList[0]?.originFileObj
    if (!file) {
      message.error('Выберите Excel-файл')
      return
    }
    setSubmitting(true)
    try {
      const { data } = await productionRequestsApi.upload(file, {
        client_name: values.client_name,
        valid_from: values.dates[0].format('YYYY-MM-DD'),
        valid_to: values.dates[1].format('YYYY-MM-DD'),
      })
      setUploadResult(data.data)
      message.success(data.data.message)
      if (data.data.imported_count > 0) {
        await load()
        onNormativesChanged()
      }
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось загрузить нормативы'))
    } finally {
      setSubmitting(false)
    }
  }

  const openDates = () => {
    if (!selected) {
      return
    }
    datesForm.setFieldsValue({
      dates: [dayjs(selected.valid_from), dayjs(selected.valid_to)],
    })
    setDatesOpen(true)
  }

  const submitDates = async () => {
    if (!selected) {
      return
    }
    const values = await datesForm.validateFields()
    setSubmitting(true)
    try {
      await productionRequestsApi.updateDates(selected.id, {
        valid_from: values.dates[0].format('YYYY-MM-DD'),
        valid_to: values.dates[1].format('YYYY-MM-DD'),
      })
      message.success('Даты партии обновлены')
      setDatesOpen(false)
      await load()
      onNormativesChanged()
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось изменить даты'))
    } finally {
      setSubmitting(false)
    }
  }

  const removeSelected = async () => {
    if (!selected) {
      return
    }
    setSubmitting(true)
    try {
      await productionRequestsApi.remove(selected.id)
      message.success('Партия и связанные нормативы удалены')
      setSelectedId(undefined)
      await load()
      onNormativesChanged()
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось удалить партию'))
    } finally {
      setSubmitting(false)
    }
  }

  const downloadTemplate = async () => {
    try {
      const { data } = await productionRequestsApi.downloadTemplate()
      downloadBlob(data, 'production_normatives_template.xlsx')
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось скачать шаблон'))
    }
  }

  const columns: ColumnsType<ProductionRequestListItem> = [
    {
      title: 'Партия',
      dataIndex: 'batch_id',
      width: 110,
      render: (value: string) => value.slice(0, 8),
    },
    {
      title: 'Загрузил',
      dataIndex: ['uploaded_by', 'full_name'],
    },
    {
      title: 'Общий клиент',
      dataIndex: 'client_name',
      render: (value?: string | null) => value || 'По строкам файла',
    },
    {
      title: 'Действует с',
      dataIndex: 'valid_from',
      width: 125,
      render: (value: string) => dayjs(value).format('DD.MM.YYYY'),
    },
    {
      title: 'Действует до',
      dataIndex: 'valid_to',
      width: 125,
      render: (value: string) => dayjs(value).format('DD.MM.YYYY'),
    },
    {
      title: 'Позиций',
      dataIndex: 'items_count',
      width: 100,
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      width: 110,
      render: (value: string) => (
        <Tag color={value === 'active' ? 'green' : 'default'}>
          {value === 'active' ? 'Активна' : value}
        </Tag>
      ),
    },
  ]

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Space wrap>
        <Button type="primary" icon={<UploadOutlined />} onClick={openUpload}>
          Загрузить НЗ
        </Button>
        <Button
          icon={<EditOutlined />}
          disabled={!selected}
          onClick={openDates}
        >
          Изменить даты
        </Button>
        <Popconfirm
          title="Удалить выбранную партию и все связанные нормативы?"
          okText="Удалить"
          cancelText="Отмена"
          disabled={!selected}
          onConfirm={() => void removeSelected()}
        >
          <Button
            danger
            icon={<DeleteOutlined />}
            disabled={!selected}
            loading={submitting}
          >
            Удалить партию
          </Button>
        </Popconfirm>
        <Button icon={<DownloadOutlined />} onClick={() => void downloadTemplate()}>
          Скачать шаблон
        </Button>
      </Space>

      <Typography.Text type="secondary">
        Выберите партию в таблице для изменения дат или удаления.
      </Typography.Text>
      <Table
        rowKey="id"
        loading={loading}
        dataSource={items}
        columns={columns}
        pagination={{ pageSize: 20 }}
        rowSelection={{
          type: 'radio',
          selectedRowKeys: selectedId ? [selectedId] : [],
          onChange: (keys) => setSelectedId(keys[0] as string | undefined),
        }}
      />

      <Modal
        title="Загрузить НЗ"
        open={uploadOpen}
        okText={uploadResult ? 'Закрыть' : 'Загрузить'}
        cancelText="Отмена"
        confirmLoading={submitting}
        onCancel={() => setUploadOpen(false)}
        onOk={() => {
          if (uploadResult) {
            setUploadOpen(false)
            return
          }
          void submitUpload()
        }}
      >
        <Form form={uploadForm} layout="vertical">
          <Form.Item
            label="Excel-файл"
            required
            extra="Колонки: Завод ERP, Склад ERP, Артикул, Количество, Ед., Клиент"
          >
            <Upload
              accept=".xlsx"
              maxCount={1}
              fileList={fileList}
              beforeUpload={() => false}
              onChange={({ fileList: next }) => setFileList(next.slice(-1))}
            >
              <Button icon={<UploadOutlined />}>Выбрать файл</Button>
            </Upload>
          </Form.Item>
          <Form.Item
            name="client_name"
            label="Общий клиент"
            extra="Используется, если клиент не указан в строке Excel"
          >
            <Input maxLength={500} />
          </Form.Item>
          <Form.Item
            name="dates"
            label="Период действия"
            rules={[{ required: true, message: 'Укажите период действия' }]}
          >
            <RangePicker style={{ width: '100%' }} format="DD.MM.YYYY" />
          </Form.Item>
        </Form>
        {uploadResult ? (
          <Alert
            showIcon
            type={uploadResult.error_count > 0 ? 'warning' : 'success'}
            message={uploadResult.message}
            description={
              uploadResult.error_details.length > 0 ? (
                <Space direction="vertical" size={2}>
                  {uploadResult.error_details.map((error) => (
                    <Typography.Text type="danger" key={error.row}>
                      Строка {error.row}: {error.message}
                    </Typography.Text>
                  ))}
                </Space>
              ) : undefined
            }
          />
        ) : null}
      </Modal>

      <Modal
        title="Изменить даты партии"
        open={datesOpen}
        okText="Сохранить"
        cancelText="Отмена"
        confirmLoading={submitting}
        onCancel={() => setDatesOpen(false)}
        onOk={() => void submitDates()}
      >
        <Form form={datesForm} layout="vertical">
          <Form.Item
            name="dates"
            label="Период действия"
            rules={[{ required: true, message: 'Укажите период действия' }]}
          >
            <RangePicker style={{ width: '100%' }} format="DD.MM.YYYY" />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  )
}
