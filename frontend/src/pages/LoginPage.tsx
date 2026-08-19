import { Form, Input, Button, Card, Typography, Checkbox, message } from 'antd'
import { useNavigate, Navigate } from 'react-router-dom'
import { getApiErrorMessage } from '../api/client'
import { useAuthStore } from '../stores/auth'

interface LoginFormValues {
  username: string
  password: string
  remember?: boolean
}

export function LoginPage() {
  const navigate = useNavigate()
  const login = useAuthStore((state) => state.login)
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const isLoading = useAuthStore((state) => state.isLoading)

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  const onFinish = async (values: LoginFormValues) => {
    try {
      await login(values.username, values.password)
      message.success('Вход выполнен')
      navigate('/dashboard')
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Неверный логин или пароль'))
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#f5f5f5',
      }}
    >
      <Card style={{ width: 360 }}>
        <Typography.Title level={3} style={{ textAlign: 'center' }}>
          Standart Reserve
        </Typography.Title>
        <Form layout="vertical" onFinish={onFinish} initialValues={{ remember: true }}>
          <Form.Item
            label="Логин"
            name="username"
            rules={[{ required: true, message: 'Введите логин' }]}
          >
            <Input autoComplete="username" />
          </Form.Item>
          <Form.Item
            label="Пароль"
            name="password"
            rules={[{ required: true, message: 'Введите пароль' }]}
          >
            <Input.Password autoComplete="current-password" />
          </Form.Item>
          <Form.Item name="remember" valuePropName="checked">
            <Checkbox>Запомнить меня</Checkbox>
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block loading={isLoading}>
              Войти
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}
