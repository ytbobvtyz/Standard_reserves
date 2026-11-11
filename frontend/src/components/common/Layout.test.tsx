import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { AppLayout } from './Layout'
import { useAuthStore } from '../../stores/auth'

function renderLayout(role: 'logistics' | 'commercial' | 'admin') {
  useAuthStore.setState({
    user: {
      id: role === 'logistics' ? '4444' : role === 'admin' ? '6666' : '1111',
      username: role,
      full_name:
        role === 'logistics'
          ? 'Кузнецов Кузьма'
          : role === 'admin'
            ? 'Администратор'
            : 'Иванов Иван',
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
    expect(screen.getByText('Клиенты')).toBeTruthy()
    expect(screen.getByText('История доступных остатков')).toBeTruthy()
    expect(screen.queryByText('Журнал действий')).toBeNull()
  })

  it('shows the audit journal only for admin', () => {
    renderLayout('admin')
    expect(screen.getByText('Администрирование')).toBeTruthy()
    expect(screen.getByText('Журнал действий')).toBeTruthy()
    expect(screen.getByText('Создать запрос')).toBeTruthy()
  })

  it('hides administration item for commercial', () => {
    renderLayout('commercial')
    expect(screen.queryByText('Администрирование')).toBeNull()
    expect(screen.getByText('Клиенты')).toBeTruthy()
    expect(screen.getByText('Продажи')).toBeTruthy()
    expect(screen.getByText('Аналитика')).toBeTruthy()
  })

  it('shows change password action', () => {
    renderLayout('commercial')
    expect(screen.getByText('Сменить пароль')).toBeTruthy()
  })
})
