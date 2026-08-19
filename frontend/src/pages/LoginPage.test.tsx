import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { LoginPage } from './LoginPage'

describe('LoginPage', () => {
  it('renders login form', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )
    expect(screen.getByText('Standart Reserve')).toBeTruthy()
    expect(screen.getByLabelText('Логин')).toBeTruthy()
    expect(screen.getByLabelText('Пароль')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Войти' })).toBeTruthy()
  })
})
