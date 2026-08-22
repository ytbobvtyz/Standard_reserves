import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ObjectsPage } from './ObjectsPage'
import { useAuthStore } from '../stores/auth'
import type { ObjectListItem } from '../api/types'

const warehouse: ObjectListItem = {
  code: 2001,
  name: 'Склад Ростов',
  city: 'Ростов-на-Дону',
  region: 'Ростовская область',
  type: 'warehouse',
  erp_plant_code: null,
  erp_warehouse_code: 'F005',
  loading_point: '2R05',
  is_active: true,
  last_modified_at: '2026-08-20T12:00:00Z',
}

const getObjects = vi.fn()
const getObjectForEdit = vi.fn()
const createObject = vi.fn()
const updateObject = vi.fn()
const deleteObject = vi.fn()

vi.mock('../api/references', () => ({
  referencesApi: {
    getObjects: (...args: unknown[]) => getObjects(...args),
    getObjectForEdit: (...args: unknown[]) => getObjectForEdit(...args),
    createObject: (...args: unknown[]) => createObject(...args),
    updateObject: (...args: unknown[]) => updateObject(...args),
    deleteObject: (...args: unknown[]) => deleteObject(...args),
  },
}))

function setRole(role: 'logistics' | 'commercial') {
  useAuthStore.setState({
    user: {
      id: '44444444-4444-4444-4444-444444444444',
      username: role,
      full_name: role === 'logistics' ? 'Кузнецов Кузьма' : 'Иванов Иван',
      role,
    },
    token: 'token',
    isAuthenticated: true,
    isLoading: false,
  })
}

describe('ObjectsPage', () => {
  beforeEach(() => {
    getObjects.mockReset()
    getObjectForEdit.mockReset()
    createObject.mockReset()
    updateObject.mockReset()
    deleteObject.mockReset()

    getObjects.mockResolvedValue({
      data: {
        status: 'success',
        data: [warehouse],
        meta: { page: 1, limit: 10, total: 1 },
      },
    })
    getObjectForEdit.mockResolvedValue({
      data: {
        status: 'success',
        data: {
          ...warehouse,
          last_modified_by: {
            id: '44444444-4444-4444-4444-444444444444',
            full_name: 'Кузнецов Кузьма',
          },
        },
      },
    })
    createObject.mockResolvedValue({
      data: { status: 'success', data: warehouse },
    })
    updateObject.mockResolvedValue({
      data: { status: 'success', data: warehouse },
    })
    deleteObject.mockResolvedValue({
      data: { status: 'success', message: 'Объект удален' },
    })
    setRole('logistics')
  })

  it('shows management buttons and last modified column for logistics', async () => {
    render(
      <MemoryRouter>
        <ObjectsPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Склад Ростов')).toBeTruthy()
    })
    expect(screen.getByRole('button', { name: /Создать объект/ })).toBeTruthy()
    expect(screen.getByText('Дата изменения')).toBeTruthy()
    expect(screen.getByRole('columnheader', { name: 'Завод' })).toBeTruthy()
    expect(screen.getByRole('columnheader', { name: 'Склад' })).toBeTruthy()
    expect(screen.getByRole('columnheader', { name: 'Пункт отгрузки' })).toBeTruthy()
    expect(screen.getByText('F005')).toBeTruthy()
    expect(screen.getByText('2R05')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Редактировать' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Удалить' })).toBeTruthy()
  })

  it('hides management buttons for commercial', async () => {
    setRole('commercial')
    render(
      <MemoryRouter>
        <ObjectsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Склад Ростов')).toBeTruthy()
    })
    expect(screen.queryByRole('button', { name: /Создать объект/ })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Редактировать' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Удалить' })).toBeNull()
  })

  it('opens create modal', async () => {
    render(
      <MemoryRouter>
        <ObjectsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Склад Ростов')).toBeTruthy()
    })
    fireEvent.click(screen.getByRole('button', { name: /Создать объект/ }))
    expect(screen.getByRole('dialog', { name: 'Создать объект' })).toBeTruthy()
    expect(screen.getByText('Наименование')).toBeTruthy()
    expect(screen.getByLabelText('Завод')).toBeTruthy()
    expect(screen.getByLabelText('Склад')).toBeTruthy()
    expect(screen.getByLabelText('Пункт отгрузки')).toBeTruthy()
    expect(screen.getByLabelText('Завод')).toHaveProperty('disabled', false)
    expect(screen.getByLabelText('Склад')).toHaveProperty('disabled', false)
    expect(screen.getByLabelText('Пункт отгрузки')).toHaveProperty('disabled', false)
    expect(screen.getByRole('button', { name: 'Создать' })).toBeTruthy()
  })

  it('opens edit modal and deletes with confirmation', async () => {
    render(
      <MemoryRouter>
        <ObjectsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Склад Ростов')).toBeTruthy()
    })
    fireEvent.click(screen.getByRole('button', { name: 'Редактировать' }))
    await waitFor(() => {
      expect(getObjectForEdit).toHaveBeenCalledWith(2001)
    })
    expect(screen.getByText('Редактировать объект')).toBeTruthy()
    expect(screen.getByDisplayValue('Склад Ростов')).toBeTruthy()
    expect(screen.getByLabelText('Завод')).toBeTruthy()
    expect(screen.getByLabelText('Склад')).toBeTruthy()
    expect(screen.getByLabelText('Пункт отгрузки')).toBeTruthy()
    expect(screen.getByDisplayValue('F005')).toBeTruthy()
    expect(screen.getByDisplayValue('2R05')).toBeTruthy()
    expect(screen.getByText('Последнее изменение')).toBeTruthy()

    const modalDelete = screen.getAllByRole('button', { name: 'Удалить' }).find(
      (button) => button.textContent === 'Удалить',
    )
    expect(modalDelete).toBeTruthy()
    fireEvent.click(modalDelete as HTMLElement)
    await waitFor(() => {
      expect(screen.getByText('Удалить объект?')).toBeTruthy()
    })
    const confirmButtons = screen.getAllByRole('button', { name: 'Удалить' })
    fireEvent.click(confirmButtons[confirmButtons.length - 1])
    await waitFor(() => {
      expect(deleteObject).toHaveBeenCalledWith(2001)
    })
  }, 15000)
})
