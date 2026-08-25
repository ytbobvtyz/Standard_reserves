import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminUsersPage } from './AdminUsersPage'
import { useAuthStore } from '../stores/auth'
import type { AdminUser, DepartmentListItem } from '../api/types'

const department: DepartmentListItem = {
  id: '66111111-1111-1111-1111-111111111111',
  name: 'Коммерческий отдел',
  is_active: true,
}

const user: AdminUser = {
  id: '11111111-1111-1111-1111-111111111111',
  username: 'commercial',
  email: 'commercial@company.ru',
  full_name: 'Иванов Иван',
  role: 'commercial',
  department_id: department.id,
  department_name: department.name,
  is_active: true,
  created_at: '2026-08-18T09:00:00Z',
  deleted_at: null,
}

const getUsers = vi.fn()
const createUser = vi.fn()
const getUser = vi.fn()
const updateUser = vi.fn()
const deleteUser = vi.fn()
const resetPassword = vi.fn()
const getDepartments = vi.fn()

vi.mock('../api/admin', () => ({
  adminApi: {
    getUsers: (...args: unknown[]) => getUsers(...args),
    createUser: (...args: unknown[]) => createUser(...args),
    getUser: (...args: unknown[]) => getUser(...args),
    updateUser: (...args: unknown[]) => updateUser(...args),
    deleteUser: (...args: unknown[]) => deleteUser(...args),
    resetPassword: (...args: unknown[]) => resetPassword(...args),
    getDepartments: (...args: unknown[]) => getDepartments(...args),
  },
}))

function setLogistics() {
  useAuthStore.setState({
    user: {
      id: '44444444-4444-4444-4444-444444444444',
      username: 'logistics',
      full_name: 'Кузнецов Кузьма',
      role: 'logistics',
    },
    token: 'token',
    isAuthenticated: true,
    isLoading: false,
  })
}

describe('AdminUsersPage', () => {
  beforeEach(() => {
    getUsers.mockReset()
    createUser.mockReset()
    getUser.mockReset()
    updateUser.mockReset()
    deleteUser.mockReset()
    resetPassword.mockReset()
    getDepartments.mockReset()

    getUsers.mockResolvedValue({
      data: {
        status: 'success',
        data: [user],
        meta: { page: 1, limit: 10, total: 1 },
      },
    })
    getDepartments.mockResolvedValue({
      data: { status: 'success', data: [department] },
    })
    getUser.mockResolvedValue({
      data: { status: 'success', data: user },
    })
    createUser.mockResolvedValue({
      data: { status: 'success', data: user },
    })
    updateUser.mockResolvedValue({
      data: { status: 'success', data: user },
    })
    deleteUser.mockResolvedValue({
      data: { status: 'success', message: 'Пользователь удален' },
    })
    resetPassword.mockResolvedValue({
      data: { status: 'success', data: { new_password: 'Ab12Cd34' } },
    })
    setLogistics()
  })

  it('renders table, filters and create button', async () => {
    render(
      <MemoryRouter>
        <AdminUsersPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Иванов Иван')).toBeTruthy()
    })
    expect(screen.getByText('Администрирование пользователей')).toBeTruthy()
    expect(screen.getByRole('button', { name: /Создать пользователя/ })).toBeTruthy()
    expect(screen.getByRole('columnheader', { name: 'Логин' })).toBeTruthy()
    expect(screen.getByRole('columnheader', { name: 'Email' })).toBeTruthy()
    expect(screen.getByRole('columnheader', { name: 'ФИО' })).toBeTruthy()
    expect(screen.getByRole('columnheader', { name: 'Роль' })).toBeTruthy()
    expect(screen.getByRole('columnheader', { name: 'Подразделение' })).toBeTruthy()
    expect(screen.getByRole('columnheader', { name: 'Статус' })).toBeTruthy()
    expect(screen.getByText('commercial')).toBeTruthy()
    expect(screen.getByText('commercial@company.ru')).toBeTruthy()
    expect(screen.getByText('Коммерческий отдел')).toBeTruthy()
    expect(screen.getByText('Активен')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Редактировать' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Сбросить пароль' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Удалить' })).toBeTruthy()
    expect(getUsers).toHaveBeenCalled()
    expect(getDepartments).toHaveBeenCalled()
  })

  it('opens create modal', async () => {
    render(
      <MemoryRouter>
        <AdminUsersPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Иванов Иван')).toBeTruthy()
    })
    fireEvent.click(screen.getByRole('button', { name: /Создать пользователя/ }))
    expect(screen.getByRole('dialog', { name: 'Создать пользователя' })).toBeTruthy()
    expect(screen.getByLabelText('Логин')).toBeTruthy()
    expect(screen.getByLabelText('Email')).toBeTruthy()
    expect(screen.getByLabelText('ФИО')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Создать' })).toBeTruthy()
  })

  it('opens edit modal with read-only username', async () => {
    render(
      <MemoryRouter>
        <AdminUsersPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Иванов Иван')).toBeTruthy()
    })
    fireEvent.click(screen.getByRole('button', { name: 'Редактировать' }))
    await waitFor(() => {
      expect(getUser).toHaveBeenCalledWith(user.id)
    })
    expect(screen.getByRole('dialog', { name: 'Редактировать пользователя' })).toBeTruthy()
    const loginInput = screen.getByDisplayValue('commercial')
    expect(loginInput).toHaveProperty('disabled', true)
  })
})
