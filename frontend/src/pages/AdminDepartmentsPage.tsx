import { Button, Form, Input, Modal, Popconfirm, Space, Table, Typography, message } from 'antd'
import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useState } from 'react'
import { adminApi } from '../api/admin'
import { getApiErrorMessage } from '../api/client'
import type { DepartmentListItem } from '../api/types'

interface DepartmentNameForm {
  name: string
}

export function AdminDepartmentsPage() {
  const [items, setItems] = useState<DepartmentListItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [renameOpen, setRenameOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [editing, setEditing] = useState<DepartmentListItem | null>(null)
  const [createForm] = Form.useForm<DepartmentNameForm>()
  const [renameForm] = Form.useForm<DepartmentNameForm>()

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await adminApi.getDepartments()
      setItems(data.data)
    } catch (err) {
      setError(getApiErrorMessage(err, 'Не удалось загрузить подразделения'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const openCreate = () => {
    createForm.resetFields()
    setCreateOpen(true)
  }

  const createDepartment = async () => {
    const values = await createForm.validateFields()
    setCreating(true)
    try {
      await adminApi.createDepartment({ name: values.name.trim() })
      message.success('Подразделение создано')
      setCreateOpen(false)
      await load()
    } catch (err) {
      message.error(getApiErrorMessage(err, 'Не удалось создать подразделение'))
    } finally {
      setCreating(false)
    }
  }

  const openRename = (item: DepartmentListItem) => {
    setEditing(item)
    renameForm.setFieldsValue({ name: item.name })
    setRenameOpen(true)
  }

  const renameDepartment = async () => {
    if (!editing) {
      return
    }
    const values = await renameForm.validateFields()
    setSaving(true)
    try {
      await adminApi.updateDepartment(editing.id, { name: values.name.trim() })
      message.success('Подразделение переименовано')
      setRenameOpen(false)
      setEditing(null)
      await load()
    } catch (err) {
      message.error(getApiErrorMessage(err, 'Не удалось переименовать подразделение'))
    } finally {
      setSaving(false)
    }
  }

  const deleteDepartment = async (id: string) => {
    setDeleting(true)
    try {
      await adminApi.deleteDepartment(id)
      message.success('Подразделение удалено')
      await load()
    } catch (err) {
      message.error(getApiErrorMessage(err, 'Не удалось удалить подразделение'))
    } finally {
      setDeleting(false)
    }
  }

  const columns: ColumnsType<DepartmentListItem> = [
    { title: 'Название', dataIndex: 'name' },
    {
      title: 'Пользователей',
      dataIndex: 'users_count',
      width: 160,
      render: (value?: number) => value ?? 0,
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 120,
      render: (_value, record) => {
        const hasUsers = (record.users_count ?? 0) > 0
        return (
          <Space>
            <Button
              type="text"
              aria-label="Переименовать"
              icon={<EditOutlined aria-hidden />}
              onClick={() => openRename(record)}
            />
            <Popconfirm
              title="Удалить подразделение?"
              description={
                hasUsers
                  ? 'Нельзя удалить: есть назначенные пользователи'
                  : `Удалить «${record.name}»?`
              }
              okText="Удалить"
              cancelText="Отмена"
              okButtonProps={{ danger: true, loading: deleting, disabled: hasUsers }}
              onConfirm={() => {
                if (!hasUsers) {
                  void deleteDepartment(record.id)
                }
              }}
            >
              <Button
                type="text"
                danger
                aria-label="Удалить"
                icon={<DeleteOutlined aria-hidden />}
              />
            </Popconfirm>
          </Space>
        )
      },
    },
  ]

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={3}>Администрирование подразделений</Typography.Title>
      <Button type="primary" icon={<PlusOutlined aria-hidden />} onClick={openCreate}>
        Создать подразделение
      </Button>
      {error ? <Typography.Text type="danger">{error}</Typography.Text> : null}
      <Table rowKey="id" loading={loading} dataSource={items} pagination={false} columns={columns} />

      <Modal
        title="Создать подразделение"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        confirmLoading={creating}
        onOk={() => void createDepartment()}
        okText="Создать"
        destroyOnHidden
      >
        <Form form={createForm} layout="vertical">
          <Form.Item
            name="name"
            label="Название"
            rules={[{ required: true, message: 'Укажите название' }]}
          >
            <Input />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Переименовать подразделение"
        open={renameOpen}
        onCancel={() => {
          setRenameOpen(false)
          setEditing(null)
        }}
        confirmLoading={saving}
        onOk={() => void renameDepartment()}
        okText="Сохранить"
        destroyOnHidden
      >
        <Form form={renameForm} layout="vertical">
          <Form.Item
            name="name"
            label="Название"
            rules={[{ required: true, message: 'Укажите название' }]}
          >
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  )
}
