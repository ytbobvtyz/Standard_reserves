import {
  Button,
  Checkbox,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Typography,
  message,
} from 'antd'
import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useState } from 'react'
import { getApiErrorMessage } from '../api/client'
import { referencesApi } from '../api/references'
import type {
  ObjectCreatePayload,
  ObjectDetail,
  ObjectListItem,
  ObjectType,
  ObjectUpdatePayload,
} from '../api/types'
import { useAuthStore } from '../stores/auth'
import { formatDateTime } from '../utils/format'

const TYPE_LABEL: Record<ObjectType, string> = {
  plant: 'Завод',
  warehouse: 'Склад',
}

const ERP_TOKEN = /^[A-Za-z0-9]{4}$/

function LongDistanceFormItem({ visible }: { visible: boolean }) {
  return (
    <Form.Item
      label={visible ? 'Удалённый склад' : undefined}
      name="long_distance"
      valuePropName="checked"
      hidden={!visible}
    >
      <Checkbox>Удалённый склад (железнодорожная доставка)</Checkbox>
    </Form.Item>
  )
}

function erpFields(type?: ObjectType) {
  return (
    <>
      <Form.Item
        name="erp_plant_code"
        label="Завод"
        extra="4 цифры, 1000–9999"
        rules={[
          {
            required: type === 'plant',
            message: 'Укажите код завода',
          },
          {
            type: 'number',
            min: 1000,
            max: 9999,
            message: 'Код завода должен быть 4-значным (1000-9999)',
          },
        ]}
      >
        <InputNumber min={1000} max={9999} precision={0} style={{ width: '100%' }} />
      </Form.Item>
      <Form.Item
        name="erp_warehouse_code"
        label="Склад"
        extra="4 символа (буквы или цифры)"
        rules={[
          {
            required: type === 'warehouse',
            message: 'Укажите код склада',
          },
          {
            validator: async (_, value?: string) => {
              if (!value) {
                return
              }
              if (!ERP_TOKEN.test(value)) {
                return Promise.reject(
                  new Error('Код склада должен содержать 4 символа (буквы или цифры)'),
                )
              }
            },
          },
        ]}
      >
        <Input maxLength={4} />
      </Form.Item>
      <Form.Item
        name="loading_point"
        label="Пункт отгрузки"
        extra="4 символа, опционально"
        rules={[
          {
            validator: async (_, value?: string) => {
              if (!value) {
                return
              }
              if (!ERP_TOKEN.test(value)) {
                return Promise.reject(
                  new Error('Пункт отгрузки должен содержать 4 символа (буквы или цифры)'),
                )
              }
            },
          },
        ]}
      >
        <Input maxLength={4} />
      </Form.Item>
    </>
  )
}

export function ObjectsPage() {
  const user = useAuthStore((state) => state.user)
  const canManage = user?.role === 'logistics'

  const [items, setItems] = useState<ObjectListItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [type, setType] = useState<ObjectType | undefined>()
  const [page, setPage] = useState(1)
  const [error, setError] = useState<string | null>(null)
  const limit = 10

  const [createOpen, setCreateOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [createForm] = Form.useForm<ObjectCreatePayload>()
  const [editForm] = Form.useForm<ObjectUpdatePayload>()
  const createType = Form.useWatch('type', createForm)
  const editType = Form.useWatch('type', editForm)

  const [editOpen, setEditOpen] = useState(false)
  const [editLoading, setEditLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [editing, setEditing] = useState<ObjectDetail | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await referencesApi.getObjects({ type, page, limit })
      setItems(data.data)
      setTotal(data.meta?.total ?? data.data.length)
    } catch (err) {
      setError(getApiErrorMessage(err, 'Не удалось загрузить объекты'))
    } finally {
      setLoading(false)
    }
  }, [type, page])

  useEffect(() => {
    void load()
  }, [load])

  const openCreate = () => {
    createForm.resetFields()
    createForm.setFieldsValue({ is_active: true, type: 'warehouse', long_distance: false })
    setCreateOpen(true)
  }

  const createObject = async () => {
    const values = await createForm.validateFields()
    setCreating(true)
    try {
      await referencesApi.createObject({
        ...values,
        region: values.region || null,
        address: values.address || null,
        erp_plant_code: values.erp_plant_code ?? null,
        erp_warehouse_code: values.erp_warehouse_code || null,
        loading_point: values.loading_point || null,
        is_active: values.is_active ?? true,
        long_distance: values.type === 'warehouse' ? Boolean(values.long_distance) : false,
      })
      message.success('Объект создан')
      setCreateOpen(false)
      await load()
    } catch (err) {
      message.error(getApiErrorMessage(err, 'Не удалось создать объект'))
    } finally {
      setCreating(false)
    }
  }

  const openEdit = async (code: number) => {
    setEditOpen(true)
    setEditLoading(true)
    setEditing(null)
    editForm.resetFields()
    try {
      const { data } = await referencesApi.getObjectForEdit(code)
      setEditing(data.data)
      editForm.setFieldsValue({
        name: data.data.name,
        city: data.data.city,
        region: data.data.region,
        address: data.data.address,
        type: data.data.type,
        erp_plant_code: data.data.erp_plant_code,
        erp_warehouse_code: data.data.erp_warehouse_code,
        loading_point: data.data.loading_point,
        is_active: data.data.is_active,
        long_distance: data.data.long_distance ?? false,
      })
    } catch (err) {
      message.error(getApiErrorMessage(err, 'Не удалось загрузить объект'))
      setEditOpen(false)
    } finally {
      setEditLoading(false)
    }
  }

  const saveObject = async () => {
    if (!editing) {
      return
    }
    const values = await editForm.validateFields()
    setSaving(true)
    try {
      await referencesApi.updateObject(editing.code, {
        name: values.name,
        city: values.city,
        region: values.region || null,
        address: values.address || null,
        type: values.type,
        erp_plant_code: values.erp_plant_code ?? null,
        erp_warehouse_code: values.erp_warehouse_code || null,
        loading_point: values.loading_point || null,
        is_active: values.is_active,
        long_distance: values.type === 'warehouse' ? Boolean(values.long_distance) : false,
      })
      message.success('Объект сохранён')
      setEditOpen(false)
      await load()
    } catch (err) {
      message.error(getApiErrorMessage(err, 'Не удалось сохранить объект'))
    } finally {
      setSaving(false)
    }
  }

  const deleteObject = async (code: number, closeEdit = false) => {
    setDeleting(true)
    try {
      await referencesApi.deleteObject(code)
      message.success('Объект удалён')
      if (closeEdit) {
        setEditOpen(false)
      }
      await load()
    } catch (err) {
      message.error(getApiErrorMessage(err, 'Не удалось удалить объект'))
    } finally {
      setDeleting(false)
    }
  }

  const columns: ColumnsType<ObjectListItem> = [
    { title: 'Код', dataIndex: 'code', width: 100 },
    { title: 'Название', dataIndex: 'name' },
    {
      title: 'Тип',
      dataIndex: 'type',
      width: 120,
      render: (value: ObjectType) => TYPE_LABEL[value] ?? value,
    },
    { title: 'Город', dataIndex: 'city' },
    {
      title: 'Завод',
      dataIndex: 'erp_plant_code',
      width: 100,
      render: (value?: number | null) => value ?? '—',
    },
    {
      title: 'Склад',
      dataIndex: 'erp_warehouse_code',
      width: 100,
      render: (value?: string | null) => value || '—',
    },
    {
      title: 'Пункт отгрузки',
      dataIndex: 'loading_point',
      width: 140,
      render: (value?: string | null) => value || '—',
    },
    {
      title: 'Удалённый',
      dataIndex: 'long_distance',
      width: 110,
      render: (value: boolean | undefined, record) =>
        record.type === 'warehouse' && value ? 'Да' : '—',
    },
    { title: 'Регион', dataIndex: 'region' },
    {
      title: 'Дата изменения',
      dataIndex: 'last_modified_at',
      width: 170,
      render: (value?: string | null) => formatDateTime(value),
    },
  ]

  if (canManage) {
    columns.push({
      title: '',
      key: 'actions',
      width: 90,
      render: (_value, record) => (
        <Space>
          <Button
            type="text"
            aria-label="Редактировать"
            icon={<EditOutlined aria-hidden />}
            onClick={() => void openEdit(record.code)}
          />
          <Popconfirm
            title="Удалить объект?"
            description="Действие нельзя отменить, если нет связанных записей."
            okText="Удалить"
            cancelText="Отмена"
            okButtonProps={{ danger: true, loading: deleting }}
            onConfirm={() => void deleteObject(record.code)}
          >
            <Button
              type="text"
              danger
              aria-label="Удалить"
              icon={<DeleteOutlined aria-hidden />}
            />
          </Popconfirm>
        </Space>
      ),
    })
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={3}>Справочник: объекты</Typography.Title>
      <Space wrap>
        <Select
          allowClear
          placeholder="Тип объекта"
          style={{ width: 200 }}
          value={type}
          onChange={(value) => {
            setPage(1)
            setType(value)
          }}
          options={[
            { value: 'plant', label: 'Заводы' },
            { value: 'warehouse', label: 'Склады' },
          ]}
        />
        {canManage ? (
          <Button type="primary" icon={<PlusOutlined aria-hidden />} onClick={openCreate}>
            Создать объект
          </Button>
        ) : null}
      </Space>
      {error ? <Typography.Text type="danger">{error}</Typography.Text> : null}
      <Table
        rowKey="code"
        loading={loading}
        dataSource={items}
        pagination={{
          current: page,
          pageSize: limit,
          total,
          onChange: setPage,
        }}
        columns={columns}
      />

      <Modal
        title="Создать объект"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        confirmLoading={creating}
        onOk={() => void createObject()}
        okText="Создать"
        width={560}
        destroyOnHidden
      >
        <Form form={createForm} layout="vertical">
          <Form.Item
            name="code"
            label="Внутренний код"
            rules={[{ required: true, message: 'Укажите код' }]}
          >
            <InputNumber min={1} precision={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="name"
            label="Наименование"
            rules={[{ required: true, message: 'Укажите наименование' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="city"
            label="Город"
            rules={[{ required: true, message: 'Укажите город' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="region" label="Регион">
            <Input />
          </Form.Item>
          <Form.Item name="address" label="Адрес">
            <Input />
          </Form.Item>
          <Form.Item
            name="type"
            label="Тип"
            rules={[{ required: true, message: 'Выберите тип' }]}
          >
            <Select
              options={[
                { value: 'plant', label: 'Завод' },
                { value: 'warehouse', label: 'Склад' },
              ]}
              onChange={(value) => {
                if (value !== 'warehouse') {
                  createForm.setFieldValue('long_distance', false)
                }
              }}
            />
          </Form.Item>
          {erpFields(createType ?? 'warehouse')}
          <LongDistanceFormItem visible={(createType ?? 'warehouse') === 'warehouse'} />
          <Form.Item name="is_active" valuePropName="checked">
            <Checkbox>Активен</Checkbox>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Редактировать объект"
        open={editOpen}
        onCancel={() => setEditOpen(false)}
        confirmLoading={saving}
        onOk={() => void saveObject()}
        okText="Сохранить"
        width={560}
        footer={(_, { OkBtn, CancelBtn }) => (
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <Popconfirm
              title="Удалить объект?"
              description="Действие нельзя отменить, если нет связанных записей."
              okText="Удалить"
              cancelText="Отмена"
              okButtonProps={{ danger: true, loading: deleting }}
              onConfirm={() => {
                if (editing) {
                  void deleteObject(editing.code, true)
                }
              }}
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
        <Form form={editForm} layout="vertical" disabled={editLoading}>
          <Form.Item label="Код">
            <Input value={editing?.code} disabled />
          </Form.Item>
          <Form.Item
            name="name"
            label="Наименование"
            rules={[{ required: true, message: 'Укажите наименование' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="city"
            label="Город"
            rules={[{ required: true, message: 'Укажите город' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="region" label="Регион">
            <Input />
          </Form.Item>
          <Form.Item name="address" label="Адрес">
            <Input />
          </Form.Item>
          <Form.Item
            name="type"
            label="Тип"
            rules={[{ required: true, message: 'Выберите тип' }]}
          >
            <Select
              options={[
                { value: 'plant', label: 'Завод' },
                { value: 'warehouse', label: 'Склад' },
              ]}
              onChange={(value) => {
                if (value !== 'warehouse') {
                  editForm.setFieldValue('long_distance', false)
                }
              }}
            />
          </Form.Item>
          {erpFields(editType ?? editing?.type)}
          <LongDistanceFormItem
            visible={(editType ?? editing?.type) === 'warehouse'}
          />
          <Form.Item name="is_active" valuePropName="checked">
            <Checkbox>Активен</Checkbox>
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
