import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { AppLayout } from './Layout'
import { useAuthStore } from '../../stores/auth'

function renderLayout(role: 'logistics' | 'commercial') {
  useAuthStore.setState({
    user: {
      id: role === 'logistics' ? '4444' : '1111',
      username: role,
      full_name: role === 'logistics' ? 'Кузнецов Кузьма' : 'Иванов Иван',
      role,
    },
    token: 'token',
    isAuthenticated: true,
    isLoading: false,
  })
  return render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<div>Дашборд</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('AppLayout admin menu', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
    })
  })

  it('shows administration submenu for logistics', () => {
    renderLayout('logistics')
    expect(screen.getByText('Администрирование')).toBeTruthy()
    expect(screen.getByText('Пользователи')).toBeTruthy()
    expect(screen.getByText('Подразделения')).toBeTruthy()
  })

  it('hides administration item for commercial', () => {
    renderLayout('commercial')
    expect(screen.queryByText('Администрирование')).toBeNull()
  })

  it('shows change password action', () => {
    renderLayout('commercial')
    expect(screen.getByText('Сменить пароль')).toBeTruthy()
  })
})
