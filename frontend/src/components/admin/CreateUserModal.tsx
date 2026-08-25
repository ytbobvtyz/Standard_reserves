import { Form, Input, Modal, Select } from 'antd'
import type { DepartmentListItem, UserRole } from '../../api/types'
import { PasswordStrengthField } from '../common/PasswordStrengthField'
import { ROLE_OPTIONS } from './roles'

export interface CreateUserFormValues {
  username: string
  email: string
  full_name: string
  role: UserRole
  department_id?: string | null
  password: string
}

interface CreateUserModalProps {
  open: boolean
  loading: boolean
  departments: DepartmentListItem[]
  onCancel: () => void
  onSubmit: (values: CreateUserFormValues) => Promise<void>
}

export function CreateUserModal({
  open,
  loading,
  departments,
  onCancel,
  onSubmit,
}: CreateUserModalProps) {
  const [form] = Form.useForm<CreateUserFormValues>()

  return (
    <Modal
      title="Создать пользователя"
      open={open}
      onCancel={onCancel}
      confirmLoading={loading}
      onOk={() => void form.validateFields().then((values) => onSubmit(values))}
      okText="Создать"
      destroyOnHidden
      afterOpenChange={(visible) => {
        if (visible) {
          form.resetFields()
        }
      }}
    >
      <Form form={form} layout="vertical">
        <Form.Item
          name="username"
          label="Логин"
          rules={[{ required: true, message: 'Укажите логин' }]}
        >
          <Input autoComplete="off" />
        </Form.Item>
        <Form.Item
          name="email"
          label="Email"
          rules={[
            { required: true, message: 'Укажите email' },
            { type: 'email', message: 'Некорректный email' },
          ]}
        >
          <Input autoComplete="off" />
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
        <PasswordStrengthField />
      </Form>
    </Modal>
  )
}
