export const PASSWORD_MIN_LENGTH = 8

export const PASSWORD_REQUIREMENTS_MESSAGE =
  'Пароль должен содержать минимум 8 символов, заглавную и строчную буквы, цифру и специальный символ'

const SPECIAL_RE = /[!@#$%^&*()_+\-=[\]{};:"\\|,.<>/?]/

export interface PasswordChecks {
  length: boolean
  upper: boolean
  lower: boolean
  digit: boolean
  special: boolean
}

export function getPasswordChecks(password: string): PasswordChecks {
  return {
    length: password.length >= PASSWORD_MIN_LENGTH,
    upper: /[A-Z]/.test(password),
    lower: /[a-z]/.test(password),
    digit: /[0-9]/.test(password),
    special: SPECIAL_RE.test(password),
  }
}

export function passwordStrengthScore(password: string): number {
  return Object.values(getPasswordChecks(password)).filter(Boolean).length
}

export function isPasswordStrong(password: string): boolean {
  return passwordStrengthScore(password) === 5
}

export const PASSWORD_CHECK_LABELS: Array<{
  key: keyof PasswordChecks
  label: string
}> = [
  { key: 'length', label: 'Минимум 8 символов' },
  { key: 'upper', label: 'Заглавная буква' },
  { key: 'lower', label: 'Строчная буква' },
  { key: 'digit', label: 'Цифра' },
  { key: 'special', label: 'Специальный символ' },
]
