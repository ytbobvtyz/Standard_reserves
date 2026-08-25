import {
  Button,
  Input,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd'
import {
  DeleteOutlined,
  EditOutlined,
  KeyOutlined,
  PlusOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useState } from 'react'
import { adminApi } from '../api/admin'
import { getApiErrorMessage } from '../api/client'
import type {
  AdminUser,
  DepartmentListItem,
  UserRole,
} from '../api/types'
import {
  CreateUserModal,
  type CreateUserFormValues,
} from '../components/admin/CreateUserModal'
import {
  EditUserModal,
  type EditUserFormValues,
} from '../components/admin/EditUserModal'
import { ResetPasswordModal } from '../components/admin/ResetPasswordModal'
import { ROLE_LABEL, ROLE_OPTIONS } from '../components/admin/roles'
import { useAuthStore } from '../stores/auth'

type StatusFilter = 'active' | 'deleted' | undefined

function userStatus(user: AdminUser): { label: string; color: string } {
  if (user.deleted_at) {
    return { label: 'Удалён', color: 'red' }
  }
  if (user.is_active) {
    return { label: 'Активен', color: 'green' }
  }
  return { label: 'Заблокирован', color: 'orange' }
}

export function AdminUsersPage() {
  const currentUser = useAuthStore((state) => state.user)

  const [items, setItems] = useState<AdminUser[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [role, setRole] = useState<UserRole | undefined>()
  const [departmentId, setDepartmentId] = useState<string | undefined>()
  const [status, setStatus] = useState<StatusFilter>()
  const [page, setPage] = useState(1)
  const [error, setError] = useState<string | null>(null)
  const [departments, setDepartments] = useState<DepartmentListItem[]>([])
  const limit = 10

  const [createOpen, setCreateOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [editLoading, setEditLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [editing, setEditing] = useState<AdminUser | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [resetOpen, setResetOpen] = useState(false)
  const [newPassword, setNewPassword] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await adminApi.getUsers({
        search: search || undefined,
        role,
        department_id: departmentId,
        is_active: status === 'active' ? true : undefined,
        deleted: status === 'deleted' ? true : undefined,
        page,
        limit,
      })
      setItems(data.data)
      setTotal(data.meta?.total ?? data.data.length)
    } catch (err) {
      setError(getApiErrorMessage(err, 'Не удалось загрузить пользователей'))
    } finally {
      setLoading(false)
    }
  }, [search, role, departmentId, status, page])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    void adminApi
      .getDepartments()
      .then(({ data }) => setDepartments(data.data))
      .catch(() => {
        setDepartments([])
      })
  }, [])

  const createUser = async (values: CreateUserFormValues) => {
    setCreating(true)
    try {
      await adminApi.createUser({
        ...values,
        department_id: values.department_id || null,
      })
      message.success('Пользователь создан')
      setCreateOpen(false)
      setPage(1)
      await load()
    } catch (err) {
      message.error(getApiErrorMessage(err, 'Не удалось создать пользователя'))
    } finally {
      setCreating(false)
    }
  }

  const openEdit = async (id: string) => {
    setEditOpen(true)
    setEditLoading(true)
    setEditing(null)
    try {
      const { data } = await adminApi.getUser(id)
      setEditing(data.data)
    } catch (err) {
      message.error(getApiErrorMessage(err, 'Не удалось загрузить пользователя'))
      setEditOpen(false)
    } finally {
      setEditLoading(false)
    }
  }

  const saveUser = async (values: EditUserFormValues) => {
    if (!editing) {
      return
    }
    setSaving(true)
    try {
      await adminApi.updateUser(editing.id, {
        email: values.email,
        full_name: values.full_name,
        role: values.role,
        department_id: values.department_id || null,
        is_active: values.is_active,
      })
      message.success('Пользователь сохранён')
      setEditOpen(false)
      await load()
    } catch (err) {
      message.error(getApiErrorMessage(err, 'Не удалось сохранить пользователя'))
    } finally {
      setSaving(false)
    }
  }

  const deleteUser = async (id: string) => {
    setDeleting(true)
    try {
      await adminApi.deleteUser(id)
      message.success('Пользователь удалён')
      await load()
    } catch (err) {
      message.error(getApiErrorMessage(err, 'Не удалось удалить пользователя'))
    } finally {
      setDeleting(false)
    }
  }

  const resetPassword = async (id: string) => {
    try {
      const { data } = await adminApi.resetPassword(id)
      setNewPassword(data.data.new_password)
      setResetOpen(true)
    } catch (err) {
      message.error(getApiErrorMessage(err, 'Не удалось сбросить пароль'))
    }
  }

  const columns: ColumnsType<AdminUser> = [
    { title: 'Логин', dataIndex: 'username' },
    { title: 'Email', dataIndex: 'email' },
    { title: 'ФИО', dataIndex: 'full_name' },
    {
      title: 'Роль',
      dataIndex: 'role',
      width: 140,
      render: (value: UserRole) => ROLE_LABEL[value] ?? value,
    },
    {
      title: 'Подразделение',
      dataIndex: 'department_name',
      render: (value?: string | null) => value || '—',
    },
    {
      title: 'Статус',
      key: 'status',
      width: 140,
      render: (_value, record) => {
        const item = userStatus(record)
        return <Tag color={item.color}>{item.label}</Tag>
      },
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 140,
      render: (_value, record) => {
        const isSelf = record.id === currentUser?.id
        const isDeleted = Boolean(record.deleted_at)
        return (
          <Space>
            <Button
              type="text"
              aria-label="Редактировать"
              icon={<EditOutlined aria-hidden />}
              disabled={isDeleted}
              onClick={() => void openEdit(record.id)}
            />
            <Popconfirm
              title="Сбросить пароль?"
              description="Будет создан новый пароль. Текущие сессии пользователя завершатся."
              okText="Сбросить"
              cancelText="Отмена"
              onConfirm={() => void resetPassword(record.id)}
            >
              <Button
                type="text"
                aria-label="Сбросить пароль"
                icon={<KeyOutlined aria-hidden />}
                disabled={isDeleted}
              />
            </Popconfirm>
            {isSelf || isDeleted ? null : (
              <Popconfirm
                title="Удалить пользователя?"
                description={`Удалить ${record.full_name}?`}
                okText="Удалить"
                cancelText="Отмена"
                okButtonProps={{ danger: true, loading: deleting }}
                onConfirm={() => void deleteUser(record.id)}
              >
                <Button
                  type="text"
                  danger
                  aria-label="Удалить"
                  icon={<DeleteOutlined aria-hidden />}
                />
              </Popconfirm>
            )}
          </Space>
        )
      },
    },
  ]

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={3}>Администрирование пользователей</Typography.Title>
      <Space wrap>
        <Input.Search
          allowClear
          placeholder="Поиск: логин, email, ФИО"
          style={{ width: 280 }}
          onSearch={(value) => {
            setPage(1)
            setSearch(value.trim())
          }}
        />
        <Select
          allowClear
          placeholder="Роль"
          style={{ width: 180 }}
          value={role}
          options={ROLE_OPTIONS}
          onChange={(value) => {
            setPage(1)
            setRole(value)
          }}
        />
        <Select
          allowClear
          placeholder="Подразделение"
          style={{ width: 240 }}
          value={departmentId}
          options={departments.map((item) => ({
            value: item.id,
            label: item.name,
          }))}
          onChange={(value) => {
            setPage(1)
            setDepartmentId(value)
          }}
        />
        <Select
          allowClear
          placeholder="Статус"
          style={{ width: 160 }}
          value={status}
          options={[
            { value: 'active', label: 'Активен' },
            { value: 'deleted', label: 'Удалён' },
          ]}
          onChange={(value) => {
            setPage(1)
            setStatus(value)
          }}
        />
        <Button
          type="primary"
          icon={<PlusOutlined aria-hidden />}
          onClick={() => setCreateOpen(true)}
        >
          Создать пользователя
        </Button>
      </Space>
      {error ? <Typography.Text type="danger">{error}</Typography.Text> : null}
      <Table
        rowKey="id"
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

      <CreateUserModal
        open={createOpen}
        loading={creating}
        departments={departments}
        onCancel={() => setCreateOpen(false)}
        onSubmit={createUser}
      />
      <EditUserModal
        open={editOpen}
        loading={editLoading}
        saving={saving}
        user={editing}
        departments={departments}
        onCancel={() => setEditOpen(false)}
        onSubmit={saveUser}
      />
      <ResetPasswordModal
        open={resetOpen}
        password={newPassword}
        onClose={() => {
          setResetOpen(false)
          setNewPassword(null)
        }}
      />
    </Space>
  )
}
