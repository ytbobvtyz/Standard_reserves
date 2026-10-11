import { Form, Input, Modal, Select, Switch, Typography } from 'antd'
import { useEffect } from 'react'
import { clientsApi } from '../../api/clients'
import { getApiErrorMessage } from '../../api/client'
import type { ClientListItem, DepartmentListItem } from '../../api/types'

const SYSTEM_CODE = '9999999999'
const NO_DEPARTMENT = '__none__'

export interface ClientFormValues {
  client_code?: string
  inn?: string
  name: string
  kpp?: string
  department_id?: string
  is_active?: boolean
}

interface ClientFormModalProps {
  open: boolean
  mode: 'create-request' | 'create-admin' | 'edit'
  client?: ClientListItem | null
  departmentName?: string | null
  canCreate: boolean
  departments?: DepartmentListItem[]
  confirmLoading?: boolean
  onCancel: () => void
  onSubmit: (values: ClientFormValues) => Promise<void>
}

export function digitsRule(length: number, label: string) {
  return {
    validator: async (_rule: unknown, value: string | undefined) => {
      const text = (value ?? '').trim()
      if (!text) {
        return
      }
      if (!new RegExp(`^\\d{${length}}$`).test(text)) {
        throw new Error(`${label}: ${length} цифр`)
      }
    },
  }
}

export function ClientFormModal({
  open,
  mode,
  client,
  departmentName,
  canCreate,
  departments = [],
  confirmLoading,
  onCancel,
  onSubmit,
}: ClientFormModalProps) {
  const [form] = Form.useForm<ClientFormValues>()
  const editing = mode === 'edit'

  useEffect(() => {
    if (!open) {
      return
    }
    if (editing && client) {
      form.setFieldsValue({
        client_code: String(client.client_code),
        inn: client.inn,
        name: client.name,
        kpp: client.kpp ?? '',
        department_id: client.department_id ?? NO_DEPARTMENT,
        is_active: client.is_active,
      })
      return
    }
    form.resetFields()
    form.setFieldsValue({ is_active: true, department_id: NO_DEPARTMENT })
  }, [open, editing, client, form])

  const title =
    mode === 'edit'
      ? 'Изменить клиента'
      : mode === 'create-admin'
        ? 'Создать клиента'
        : 'Создать клиента'

  return (
    <Modal
      title={title}
      open={open}
      okText={editing ? 'Сохранить' : 'Создать'}
      cancelText="Отмена"
      confirmLoading={confirmLoading}
      okButtonProps={{ disabled: !editing && !canCreate }}
      onCancel={onCancel}
      onOk={() => {
        void form.validateFields().then((values) => onSubmit(values))
      }}
      destroyOnHidden
    >
      {!editing && !canCreate ? (
        <Typography.Paragraph type="danger">
          У пользователя не задано подразделение
        </Typography.Paragraph>
      ) : null}
      {mode === 'create-request' && canCreate ? (
        <Typography.Paragraph type="secondary">
          {departmentName
            ? `Будет привязан к ${departmentName}`
            : 'Будет привязан к подразделению пользователя'}
        </Typography.Paragraph>
      ) : null}
      <Form form={form} layout="vertical">
        <Form.Item
          name="client_code"
          label="ID клиента (КССС)"
          rules={
            editing
              ? []
              : [
                  { required: true, message: 'Укажите код КССС' },
                  {
                    validator: async (_rule, value: string | undefined) => {
                      const text = (value ?? '').trim()
                      if (!/^\d{1,10}$/.test(text)) {
                        throw new Error('Целое число до 10 знаков')
                      }
                      if (text === SYSTEM_CODE || Number(text) < 1) {
                        throw new Error('Код 9999999999 зарезервирован')
                      }
                    },
                  },
                ]
          }
        >
          <Input inputMode="numeric" maxLength={10} disabled={editing} />
        </Form.Item>
        <Form.Item
          name="inn"
          label="ИНН"
          rules={
            editing
              ? []
              : [
                  { required: true, message: 'Укажите ИНН' },
                  {
                    validator: async (_rule, value: string | undefined) => {
                      const text = (value ?? '').trim()
                      if (!/^(\d{10}|\d{12})$/.test(text) || text === '0000000000') {
                        throw new Error('ИНН — 10 или 12 цифр')
                      }
                    },
                  },
                ]
          }
        >
          <Input inputMode="numeric" maxLength={12} disabled={editing} />
        </Form.Item>
        <Form.Item
          name="name"
          label="Наименование"
          rules={[{ required: true, message: 'Укажите наименование' }]}
        >
          <Input maxLength={500} />
        </Form.Item>
        <Form.Item name="kpp" label="КПП" rules={[digitsRule(9, 'КПП')]}>
          <Input inputMode="numeric" maxLength={9} />
        </Form.Item>
        {mode === 'create-admin' || mode === 'edit' ? (
          <Form.Item name="department_id" label="Управление продаж">
            <Select
              options={[
                { value: NO_DEPARTMENT, label: 'Без управления' },
                ...departments.map((item) => ({ value: item.id, label: item.name })),
              ]}
            />
          </Form.Item>
        ) : null}
        {editing ? (
          <Form.Item name="is_active" label="Активен" valuePropName="checked">
            <Switch />
          </Form.Item>
        ) : null}
      </Form>
    </Modal>
  )
}

export function departmentIdFromForm(value?: string): string | null {
  if (!value || value === NO_DEPARTMENT) {
    return null
  }
  return value
}

export async function createClientFromForm(
  values: ClientFormValues,
  mode: 'create-request' | 'create-admin',
) {
  try {
    const payload = {
      client_code: Number(values.client_code),
      inn: (values.inn ?? '').trim(),
      name: values.name.trim(),
      kpp: values.kpp?.trim() || null,
      ...(mode === 'create-admin'
        ? { department_id: departmentIdFromForm(values.department_id) }
        : {}),
    }
    const { data } = await clientsApi.create(payload)
    return data.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Не удалось создать клиента'))
  }
}
