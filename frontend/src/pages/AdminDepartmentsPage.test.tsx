import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminDepartmentsPage } from './AdminDepartmentsPage'
import type { DepartmentListItem } from '../api/types'

const emptyDepartment: DepartmentListItem = {
  id: '66111111-1111-1111-1111-111111111111',
  name: 'Пустой отдел',
  is_active: true,
  users_count: 0,
}

const usedDepartment: DepartmentListItem = {
  id: '66222222-2222-2222-2222-222222222222',
  name: 'Коммерческий отдел',
  is_active: true,
  users_count: 3,
}

const getDepartments = vi.fn()
const createDepartment = vi.fn()
const updateDepartment = vi.fn()
const deleteDepartment = vi.fn()

vi.mock('../api/admin', () => ({
  adminApi: {
    getDepartments: (...args: unknown[]) => getDepartments(...args),
    createDepartment: (...args: unknown[]) => createDepartment(...args),
    updateDepartment: (...args: unknown[]) => updateDepartment(...args),
    deleteDepartment: (...args: unknown[]) => deleteDepartment(...args),
  },
}))

describe('AdminDepartmentsPage', () => {
  beforeEach(() => {
    getDepartments.mockReset()
    createDepartment.mockReset()
    updateDepartment.mockReset()
    deleteDepartment.mockReset()

    getDepartments.mockResolvedValue({
      data: { status: 'success', data: [emptyDepartment, usedDepartment] },
    })
    createDepartment.mockResolvedValue({
      data: { status: 'success', data: emptyDepartment },
    })
    updateDepartment.mockResolvedValue({
      data: { status: 'success', data: { ...emptyDepartment, name: 'Новое имя' } },
    })
    deleteDepartment.mockResolvedValue({
      data: { status: 'success', message: 'Подразделение удалено' },
    })
  })

  it('renders table, create button and user counts', async () => {
    render(
      <MemoryRouter>
        <AdminDepartmentsPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Пустой отдел')).toBeTruthy()
    })
    expect(screen.getByText('Администрирование подразделений')).toBeTruthy()
    expect(screen.getByRole('button', { name: /Создать подразделение/ })).toBeTruthy()
    expect(screen.getByRole('columnheader', { name: 'Название' })).toBeTruthy()
    expect(screen.getByRole('columnheader', { name: 'Пользователей' })).toBeTruthy()
    expect(screen.getByText('Коммерческий отдел')).toBeTruthy()
    expect(screen.getByText('3')).toBeTruthy()
    expect(screen.getAllByRole('button', { name: 'Переименовать' })).toHaveLength(2)
    expect(screen.getAllByRole('button', { name: 'Удалить' })).toHaveLength(2)
    expect(getDepartments).toHaveBeenCalled()
  })

  it('opens create modal', async () => {
    render(
      <MemoryRouter>
        <AdminDepartmentsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Пустой отдел')).toBeTruthy()
    })
    fireEvent.click(screen.getByRole('button', { name: /Создать подразделение/ }))
    expect(screen.getByRole('dialog', { name: 'Создать подразделение' })).toBeTruthy()
    expect(screen.getByLabelText('Название')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Создать' })).toBeTruthy()
  })

  it('opens rename modal', async () => {
    render(
      <MemoryRouter>
        <AdminDepartmentsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Пустой отдел')).toBeTruthy()
    })
    fireEvent.click(screen.getAllByRole('button', { name: 'Переименовать' })[0])
    expect(screen.getByRole('dialog', { name: 'Переименовать подразделение' })).toBeTruthy()
    expect(screen.getByDisplayValue('Пустой отдел')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Сохранить' })).toBeTruthy()
  })

  it('deletes empty department after confirmation', async () => {
    render(
      <MemoryRouter>
        <AdminDepartmentsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Пустой отдел')).toBeTruthy()
    })
    fireEvent.click(screen.getAllByRole('button', { name: 'Удалить' })[0])
    await waitFor(() => {
      expect(screen.getByText('Удалить подразделение?')).toBeTruthy()
    })
    const confirmButtons = screen.getAllByRole('button', { name: 'Удалить' })
    fireEvent.click(confirmButtons[confirmButtons.length - 1])
    await waitFor(() => {
      expect(deleteDepartment).toHaveBeenCalledWith(emptyDepartment.id)
    })
  }, 15000)
})
