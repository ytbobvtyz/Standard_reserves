import { Button, Result } from 'antd'

export function ServerErrorPage() {
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
      <Result
        status="500"
        title="500"
        subTitle="Внутренняя ошибка сервера. Попробуйте обновить страницу."
        extra={
          <Button type="primary" onClick={() => window.location.assign('/')}>
            На главную
          </Button>
        }
      />
    </div>
  )
}
