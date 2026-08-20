import {
  Button,
  Checkbox,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Progress,
  Select,
  Space,
  Table,
  Typography,
  Upload,
  message,
} from 'antd'
import {
  DownloadOutlined,
  EditOutlined,
  UploadOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getApiErrorMessage } from '../api/client'
import { referencesApi } from '../api/references'
import type {
  ObjectListItem,
  ProductDetail,
  ProductListItem,
  ProductUpdatePayload,
  ProductUploadResult,
} from '../api/types'
import { ProductAutocomplete } from '../components/requests/ProductAutocomplete'
import { useAuthStore } from '../stores/auth'

const PRODUCT_MANAGERS = new Set(['pp', 'economist', 'logistics'])

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

function formatDateTime(value?: string | null): string {
  if (!value) {
    return '—'
  }
  return new Date(value).toLocaleString('ru-RU')
}

export function ProductsPage() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const canManage = Boolean(user && PRODUCT_MANAGERS.has(user.role))

  const [items, setItems] = useState<ProductListItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState<'A' | 'B' | 'C' | undefined>()
  const [page, setPage] = useState(1)
  const [error, setError] = useState<string | null>(null)
  const limit = 10

  const [uploadOpen, setUploadOpen] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<number | null>(null)
  const [uploadResult, setUploadResult] = useState<ProductUploadResult | null>(null)
  const [uploading, setUploading] = useState(false)

  const [editOpen, setEditOpen] = useState(false)
  const [editLoading, setEditLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [editing, setEditing] = useState<ProductDetail | null>(null)
  const [plants, setPlants] = useState<ObjectListItem[]>([])
  const [form] = Form.useForm<ProductUpdatePayload>()

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await referencesApi.getProducts({
        search: search || undefined,
        category,
        page,
        limit,
      })
      setItems(data.data)
      setTotal(data.meta?.total ?? data.data.length)
    } catch (err) {
      setError(getApiErrorMessage(err, 'Не удалось загрузить продукты'))
    } finally {
      setLoading(false)
    }
  }, [search, category, page])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (!canManage) {
      return
    }
    void referencesApi.getObjects({ type: 'plant', limit: 200 }).then(({ data }) => {
      setPlants(data.data)
    })
  }, [canManage])

  const downloadTemplate = async () => {
    try {
      const { data } = await referencesApi.downloadProductsTemplate()
      downloadBlob(data, 'products_template.xlsx')
    } catch (err) {
      message.error(getApiErrorMessage(err, 'Не удалось скачать шаблон'))
    }
  }

  const handleUpload = async (file: File) => {
    setUploading(true)
    setUploadProgress(0)
    setUploadResult(null)
    try {
      const { data } = await referencesApi.uploadProducts(file, setUploadProgress)
      setUploadResult(data.data)
      setUploadProgress(100)
      message.success(data.data.message)
      await load()
    } catch (err) {
      message.error(getApiErrorMessage(err, 'Не удалось загрузить файл'))
    } finally {
      setUploading(false)
    }
    return false
  }

  const openEdit = async (code: number) => {
    setEditOpen(true)
    setEditLoading(true)
    setEditing(null)
    try {
      const { data } = await referencesApi.getProductForEdit(code)
      setEditing(data.data)
      form.setFieldsValue({
        name: data.data.name,
        description: data.data.description,
        category: data.data.category as 'A' | 'B' | 'C',
        is_active: data.data.is_active,
        weight_kg: data.data.weight_kg,
        monthly_consumption: data.data.monthly_consumption,
        gtin: data.data.gtin,
        mark_control: Boolean(data.data.mark_control),
        plant_id: data.data.plant_id,
        second_plant_id: data.data.second_plant_id,
        third_plant_id: data.data.third_plant_id,
        parent_code: data.data.parent_code,
        children_code: data.data.children_code,
      })
    } catch (err) {
      message.error(getApiErrorMessage(err, 'Не удалось загрузить продукт'))
      setEditOpen(false)
    } finally {
      setEditLoading(false)
    }
  }

  const saveProduct = async () => {
    if (!editing) {
      return
    }
    const values = await form.validateFields()
    setSaving(true)
    try {
      const gtin = values.gtin?.toString().trim() || null
      await referencesApi.updateProduct(editing.code, {
        ...values,
        description: values.description || null,
        monthly_consumption: values.monthly_consumption ?? null,
        gtin,
        second_plant_id: values.second_plant_id ?? null,
        third_plant_id: values.third_plant_id ?? null,
        parent_code: values.parent_code ?? null,
        children_code: values.children_code ?? null,
      })
      message.success('Продукт сохранён')
      setEditOpen(false)
      await load()
    } catch (err) {
      message.error(getApiErrorMessage(err, 'Не удалось сохранить продукт'))
    } finally {
      setSaving(false)
    }
  }

  const deleteProduct = async () => {
    if (!editing) {
      return
    }
    setDeleting(true)
    try {
      await referencesApi.deleteProduct(editing.code)
      message.success('Продукт удалён')
      setEditOpen(false)
      await load()
    } catch (err) {
      message.error(getApiErrorMessage(err, 'Не удалось удалить продукт'))
    } finally {
      setDeleting(false)
    }
  }

  const plantOptions = plants.map((plant) => ({
    value: plant.code,
    label: `${plant.code} — ${plant.name}`,
  }))

  const columns: ColumnsType<ProductListItem> = [
    { title: 'Артикул', dataIndex: 'code', width: 110 },
    { title: 'Название', dataIndex: 'name' },
    { title: 'Категория', dataIndex: 'category', width: 100 },
    { title: 'Завод', dataIndex: 'plant_name' },
    { title: 'Вес, кг', dataIndex: 'weight_kg', width: 100 },
    {
      title: 'GTIN',
      dataIndex: 'gtin',
      width: 140,
      render: (value?: string | null) => value || '—',
    },
    {
      title: 'Честный знак',
      dataIndex: 'mark_control',
      width: 130,
      render: (value?: boolean) => (value ? 'Да' : 'Нет'),
    },
    {
      title: 'Дата изменения',
      dataIndex: 'last_modified_at',
      width: 170,
      render: (value?: string | null) => formatDateTime(value),
    },
    {
      title: 'Активен',
      dataIndex: 'is_active',
      width: 100,
      render: (value: boolean) => (value ? 'Да' : 'Нет'),
    },
  ]

  if (canManage) {
    columns.push({
      title: '',
      key: 'actions',
      width: 60,
      render: (_value, record) => (
        <Button
          type="text"
          aria-label="Редактировать"
          icon={<EditOutlined aria-hidden />}
          onClick={(event) => {
            event.stopPropagation()
            void openEdit(record.code)
          }}
        />
      ),
    })
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={3}>Справочник: продукты</Typography.Title>
      <Space wrap>
        <Input.Search
          allowClear
          placeholder="Поиск по артикулу или названию"
          style={{ width: 320 }}
          onSearch={(value) => {
            setPage(1)
            setSearch(value)
          }}
        />
        <Select
          allowClear
          placeholder="Категория"
          style={{ width: 140 }}
          value={category}
          onChange={(value) => {
            setPage(1)
            setCategory(value)
          }}
          options={[
            { value: 'A', label: 'A' },
            { value: 'B', label: 'B' },
            { value: 'C', label: 'C' },
          ]}
        />
        {canManage ? (
          <>
            <Button icon={<DownloadOutlined aria-hidden />} onClick={() => void downloadTemplate()}>
              Выгрузить шаблон
            </Button>
            <Button
              icon={<UploadOutlined aria-hidden />}
              type="primary"
              onClick={() => {
                setUploadResult(null)
                setUploadProgress(null)
                setUploadOpen(true)
              }}
            >
              Загрузить из Excel
            </Button>
          </>
        ) : null}
      </Space>
      {error ? <Typography.Text type="danger">{error}</Typography.Text> : null}
      <Table
        rowKey="code"
        loading={loading}
        dataSource={items}
        onRow={(record) => ({
          onClick: () => navigate(`/references/products/${record.code}`),
          style: { cursor: 'pointer' },
        })}
        pagination={{
          current: page,
          pageSize: limit,
          total,
          onChange: setPage,
        }}
        columns={columns}
      />

      <Modal
        title="Загрузить продукты"
        open={uploadOpen}
        onCancel={() => setUploadOpen(false)}
        footer={null}
        destroyOnHidden
      >
        <Upload.Dragger
          accept=".xlsx,.xls"
          maxCount={1}
          showUploadList={false}
          disabled={uploading}
          beforeUpload={(file) => {
            void handleUpload(file)
            return false
          }}
        >
          <p>Перетащите Excel-файл сюда или нажмите, чтобы выбрать</p>
          <p>.xlsx или .xls</p>
        </Upload.Dragger>
        {uploadProgress !== null ? (
          <Progress percent={uploadProgress} status={uploading ? 'active' : 'success'} />
        ) : null}
        {uploadResult ? (
          <Space direction="vertical" style={{ marginTop: 16, width: '100%' }}>
            <Typography.Text strong>{uploadResult.message}</Typography.Text>
            {uploadResult.error_details.map((item) => (
              <Typography.Text key={item.row} type="danger">
                Строка {item.row}: {item.message}
              </Typography.Text>
            ))}
          </Space>
        ) : null}
      </Modal>

      <Modal
        title="Редактировать продукт"
        open={editOpen}
        onCancel={() => setEditOpen(false)}
        confirmLoading={saving}
        onOk={() => void saveProduct()}
        okText="Сохранить"
        width={720}
        footer={(_, { OkBtn, CancelBtn }) => (
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <Popconfirm
              title="Удалить продукт?"
              description="Действие нельзя отменить, если нет связанных записей."
              okText="Удалить"
              cancelText="Отмена"
              okButtonProps={{ danger: true, loading: deleting }}
              onConfirm={() => void deleteProduct()}
            >
              <Button danger loading={deleting}>
                Удалить
              </Button>
            </Popconfirm>
            <Space>
              <CancelBtn />
              <OkBtn />
            </Space>
          </Space>
        )}
      >
        <Form form={form} layout="vertical" disabled={editLoading}>
          <Form.Item label="Артикул">
            <Input value={editing?.code} disabled />
          </Form.Item>
          <Form.Item
            name="name"
            label="Название"
            rules={[{ required: true, message: 'Укажите название' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="description" label="Описание">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Space wrap style={{ width: '100%' }}>
            <Form.Item
              name="category"
              label="Категория"
              rules={[{ required: true, message: 'Укажите категорию' }]}
            >
              <Select
                style={{ width: 140 }}
                options={[
                  { value: 'A', label: 'A' },
                  { value: 'B', label: 'B' },
                  { value: 'C', label: 'C' },
                ]}
              />
            </Form.Item>
            <Form.Item
              name="weight_kg"
              label="Вес, кг"
              rules={[{ required: true, message: 'Укажите вес' }]}
            >
              <InputNumber min={0.0001} step={0.01} style={{ width: 140 }} />
            </Form.Item>
            <Form.Item name="monthly_consumption" label="Потребление / мес">
              <InputNumber min={0} style={{ width: 160 }} />
            </Form.Item>
          </Space>
          <Form.Item
            name="gtin"
            label="GTIN"
            rules={[
              {
                validator: async (_, value: string | undefined) => {
                  const text = value?.trim() ?? ''
                  if (!text) {
                    return
                  }
                  if (!/^[0-9]{13}$/.test(text)) {
                    throw new Error('GTIN должен содержать 13 цифр')
                  }
                },
              },
            ]}
          >
            <Input maxLength={13} placeholder="13 цифр" />
          </Form.Item>
          <Form.Item name="mark_control" valuePropName="checked">
            <Checkbox>Честный знак</Checkbox>
          </Form.Item>
          <Form.Item name="is_active" valuePropName="checked">
            <Checkbox>Активен</Checkbox>
          </Form.Item>
          <Form.Item
            name="plant_id"
            label="Основной завод"
            rules={[{ required: true, message: 'Выберите завод' }]}
          >
            <Select options={plantOptions} />
          </Form.Item>
          <Form.Item name="second_plant_id" label="Второй завод">
            <Select allowClear options={plantOptions} />
          </Form.Item>
          <Form.Item name="third_plant_id" label="Третий завод">
            <Select allowClear options={plantOptions} />
          </Form.Item>
          <Form.Item name="parent_code" label="Родительский артикул">
            <ProductAutocomplete activeOnly={false} />
          </Form.Item>
          <Form.Item name="children_code" label="Дочерний артикул">
            <ProductAutocomplete activeOnly={false} />
          </Form.Item>
          <Form.Item label="Последнее изменение">
            <Input
              disabled
              value={
                editing
                  ? `${editing.last_modified_by?.full_name ?? '—'} · ${formatDateTime(
                      editing.last_modified_at,
                    )}`
                  : '—'
              }
            />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  )
}
