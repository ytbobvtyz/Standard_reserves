import { Alert, Input, Modal, Typography } from 'antd'

interface ResetPasswordModalProps {
  open: boolean
  password: string | null
  onClose: () => void
}

export function ResetPasswordModal({
  open,
  password,
  onClose,
}: ResetPasswordModalProps) {
  return (
    <Modal
      title="Новый пароль"
      open={open}
      onCancel={onClose}
      onOk={onClose}
      okText="Закрыть"
      cancelButtonProps={{ style: { display: 'none' } }}
    >
      <Alert
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
        message="Скопируйте пароль сейчас. Повторно он не отображается."
      />
      <Typography.Paragraph>Новый пароль пользователя:</Typography.Paragraph>
      <Input.Password value={password ?? ''} readOnly />
    </Modal>
  )
}
