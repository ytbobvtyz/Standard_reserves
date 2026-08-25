import { Form, Input, Progress, Typography } from 'antd'
import {
  getPasswordChecks,
  isPasswordStrong,
  PASSWORD_CHECK_LABELS,
  PASSWORD_REQUIREMENTS_MESSAGE,
  passwordStrengthScore,
} from '../../utils/password'

interface PasswordStrengthFieldProps {
  name?: string
  label?: string
}

function meterStatus(score: number): 'exception' | 'normal' | 'success' {
  if (score <= 2) {
    return 'exception'
  }
  if (score < 5) {
    return 'normal'
  }
  return 'success'
}

function PasswordStrengthMeter({ password }: { password: string }) {
  const checks = getPasswordChecks(password)
  const score = passwordStrengthScore(password)
  return (
    <div>
      <Progress
        percent={(score / 5) * 100}
        showInfo={false}
        size="small"
        status={meterStatus(score)}
      />
      {PASSWORD_CHECK_LABELS.map((item) => (
        <Typography.Text
          key={item.key}
          type={checks[item.key] ? 'success' : 'secondary'}
          style={{ display: 'block', fontSize: 12 }}
        >
          {checks[item.key] ? '✓' : '○'} {item.label}
        </Typography.Text>
      ))}
    </div>
  )
}

export function PasswordStrengthField({
  name = 'password',
  label = 'Пароль',
}: PasswordStrengthFieldProps) {
  const form = Form.useFormInstance()
  const value = (Form.useWatch(name, form) as string | undefined) ?? ''

  return (
    <Form.Item
      name={name}
      label={label}
      extra={<PasswordStrengthMeter password={value} />}
      rules={[
        { required: true, message: 'Укажите пароль' },
        {
          validator: async (_, candidate: string) => {
            if (!candidate) {
              return
            }
            if (!isPasswordStrong(candidate)) {
              throw new Error(PASSWORD_REQUIREMENTS_MESSAGE)
            }
          },
        },
      ]}
    >
      <Input.Password autoComplete="new-password" />
    </Form.Item>
  )
}
