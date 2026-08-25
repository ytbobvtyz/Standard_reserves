import { Form, Input, Modal, message } from 'antd'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../../api/auth'
import { getApiErrorMessage } from '../../api/client'
import { useAuthStore } from '../../stores/auth'
import { PASSWORD_REQUIREMENTS_MESSAGE } from '../../utils/password'
import { PasswordStrengthField } from './PasswordStrengthField'

interface ChangePasswordValues {
  old_password: string
  new_password: string
  confirm_password: string
}

interface ChangePasswordModalProps {
  open: boolean
  onClose: () => void
}

export function ChangePasswordModal({ open, onClose }: ChangePasswordModalProps) {
  const [form] = Form.useForm<ChangePasswordValues>()
  const [loading, setLoading] = useState(false)
  const logout = useAuthStore((state) => state.logout)
  const navigate = useNavigate()

  const handleOk = async () => {
    const values = await form.validateFields()
    setLoading(true)
    try {
      await authApi.changePassword(values.old_password, values.new_password)
      message.success('Пароль изменен. Войдите снова.')
      onClose()
      await logout()
      navigate('/login')
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось сменить пароль'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal
      title="Сменить пароль"
      open={open}
      onCancel={onClose}
      confirmLoading={loading}
      onOk={() => void handleOk()}
      okText="Сохранить"
      destroyOnHidden
      afterOpenChange={(visible) => {
        if (visible) {
          form.resetFields()
        }
      }}
    >
      <Form form={form} layout="vertical">
        <Form.Item
          name="old_password"
          label="Текущий пароль"
          rules={[{ required: true, message: 'Укажите текущий пароль' }]}
        >
          <Input.Password autoComplete="current-password" />
        </Form.Item>
        <PasswordStrengthField name="new_password" label="Новый пароль" />
        <Form.Item
          name="confirm_password"
          label="Повтор нового пароля"
          dependencies={['new_password']}
          rules={[
            { required: true, message: 'Повторите пароль' },
            ({ getFieldValue }) => ({
              validator: async (_, value: string) => {
                if (!value || getFieldValue('new_password') === value) {
                  return
                }
                throw new Error('Пароли не совпадают')
              },
            }),
          ]}
        >
          <Input.Password autoComplete="new-password" />
        </Form.Item>
        <Form.Item>
          <span style={{ color: 'rgba(0,0,0,0.45)', fontSize: 12 }}>
            {PASSWORD_REQUIREMENTS_MESSAGE}
          </span>
        </Form.Item>
      </Form>
    </Modal>
  )
}
