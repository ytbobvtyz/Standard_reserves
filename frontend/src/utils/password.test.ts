import { describe, expect, it } from 'vitest'
import {
  getPasswordChecks,
  isPasswordStrong,
  PASSWORD_REQUIREMENTS_MESSAGE,
  passwordStrengthScore,
} from './password'

describe('password strength', () => {
  it('rejects passwords that miss a required class', () => {
    expect(isPasswordStrong('password')).toBe(false)
    expect(isPasswordStrong('Password1')).toBe(false)
    expect(isPasswordStrong('PASSWORD1!')).toBe(false)
    expect(isPasswordStrong('Abc@12')).toBe(false)
  })

  it('accepts a password that meets every rule', () => {
    expect(isPasswordStrong('Abc@1234')).toBe(true)
    expect(passwordStrengthScore('Abc@1234')).toBe(5)
    expect(getPasswordChecks('Abc@1234')).toEqual({
      length: true,
      upper: true,
      lower: true,
      digit: true,
      special: true,
    })
  })

  it('exposes the user-facing requirements message', () => {
    expect(PASSWORD_REQUIREMENTS_MESSAGE).toContain('минимум 8 символов')
  })
})
