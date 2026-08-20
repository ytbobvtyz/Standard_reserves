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

const TYPE_LABEL: Record<ObjectType, string> = {
  plant: 'Завод',
  warehouse: 'Склад',
}

function formatDateTime(value?: string | null): string {
  if (!value) {
    return '—'
  }
  return new Date(value).toLocaleString('ru-RU')
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

  const [editOpen, setEditOpen] = useState(false)
  const [editLoading, setEditLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [editing, setEditing] = useState<ObjectDetail | null>(null)
  const [editForm] = Form.useForm<ObjectUpdatePayload>()

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
    createForm.setFieldsValue({ is_active: true, type: 'warehouse' })
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
        is_active: values.is_active ?? true,
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
    try {
      const { data } = await referencesApi.getObjectForEdit(code)
      setEditing(data.data)
      editForm.setFieldsValue({
        name: data.data.name,
        city: data.data.city,
        region: data.data.region,
        address: data.data.address,
        type: data.data.type,
        is_active: data.data.is_active,
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
        is_active: values.is_active,
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
        destroyOnHidden
      >
        <Form form={createForm} layout="vertical">
          <Form.Item
            name="code"
            label="Код"
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
            />
          </Form.Item>
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
            />
          </Form.Item>
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
