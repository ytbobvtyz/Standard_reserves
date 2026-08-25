import { Checkbox, Form, Input, Modal, Select } from 'antd'
import { useEffect } from 'react'
import type { AdminUser, DepartmentListItem } from '../../api/types'
import { ROLE_OPTIONS } from './roles'

export interface EditUserFormValues {
  email: string
  full_name: string
  role: AdminUser['role']
  department_id?: string | null
  is_active: boolean
}

interface EditUserModalProps {
  open: boolean
  loading: boolean
  saving: boolean
  user: AdminUser | null
  departments: DepartmentListItem[]
  onCancel: () => void
  onSubmit: (values: EditUserFormValues) => Promise<void>
}

export function EditUserModal({
  open,
  loading,
  saving,
  user,
  departments,
  onCancel,
  onSubmit,
}: EditUserModalProps) {
  const [form] = Form.useForm<EditUserFormValues>()

  useEffect(() => {
    if (open && user) {
      form.setFieldsValue({
        email: user.email,
        full_name: user.full_name,
        role: user.role,
        department_id: user.department_id ?? undefined,
        is_active: user.is_active,
      })
    }
    if (open && !user) {
      form.resetFields()
    }
  }, [form, open, user])

  return (
    <Modal
      title="Редактировать пользователя"
      open={open}
      onCancel={onCancel}
      confirmLoading={saving}
      onOk={() => void form.validateFields().then((values) => onSubmit(values))}
      okText="Сохранить"
      destroyOnHidden
    >
      <Form form={form} layout="vertical" disabled={loading}>
        <Form.Item label="Логин">
          <Input value={user?.username} disabled />
        </Form.Item>
        <Form.Item
          name="email"
          label="Email"
          rules={[
            { required: true, message: 'Укажите email' },
            { type: 'email', message: 'Некорректный email' },
          ]}
        >
          <Input />
        </Form.Item>
        <Form.Item
          name="full_name"
          label="ФИО"
          rules={[{ required: true, message: 'Укажите ФИО' }]}
        >
          <Input />
        </Form.Item>
        <Form.Item
          name="role"
          label="Роль"
          rules={[{ required: true, message: 'Выберите роль' }]}
        >
          <Select options={ROLE_OPTIONS} />
        </Form.Item>
        <Form.Item name="department_id" label="Подразделение">
          <Select
            allowClear
            placeholder="Не указано"
            options={departments.map((item) => ({
              value: item.id,
              label: item.name,
            }))}
          />
        </Form.Item>
        <Form.Item name="is_active" valuePropName="checked">
          <Checkbox>Активен</Checkbox>
        </Form.Item>
      </Form>
    </Modal>
  )
}
