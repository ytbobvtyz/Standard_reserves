import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminClientsPage } from './AdminClientsPage'
import type { ClientListItem } from '../api/types'

const list = vi.fn()
const remove = vi.fn()
const getDepartments = vi.fn()

vi.mock('../api/clients', () => ({
  clientsApi: {
    list: (...args: unknown[]) => list(...args),
    remove: (...args: unknown[]) => remove(...args),
    create: vi.fn(),
    update: vi.fn(),
    downloadTemplate: vi.fn(),
    exportExcel: vi.fn(),
    upload: vi.fn(),
  },
}))

vi.mock('../api/admin', () => ({
  adminApi: {
    getDepartments: (...args: unknown[]) => getDepartments(...args),
  },
}))

const systemClient: ClientListItem = {
  id: '00000000-0000-4000-8000-000000000001',
  client_code: 9999999999,
  inn: '0000000000',
  name: 'Общий клиент',
  kpp: null,
  department_id: null,
  department_name: null,
  is_active: true,
  is_system: true,
}

const client: ClientListItem = {
  id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  client_code: 7701000001,
  inn: '7701000001',
  name: 'ООО Ромашка',
  kpp: '770101001',
  department_id: 'dept-1',
  department_name: 'Коммерческий отдел',
  is_active: true,
  is_system: false,
}

describe('AdminClientsPage', () => {
  beforeEach(() => {
    list.mockReset()
    remove.mockReset()
    getDepartments.mockReset()
    list.mockResolvedValue({
      data: {
        status: 'success',
        data: [systemClient, client],
        meta: { page: 1, limit: 20, total: 2 },
      },
    })
    getDepartments.mockResolvedValue({
      data: { status: 'success', data: [{ id: 'dept-1', name: 'Коммерческий отдел', is_active: true }] },
    })
  })

  it('lists clients and hides actions for the system row', async () => {
    render(<AdminClientsPage />)
    expect(await screen.findByText('ООО Ромашка')).toBeTruthy()
    expect(screen.getByText('Общий клиент')).toBeTruthy()
    expect(screen.getByText('Без управления')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Изменить ООО Ромашка' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Изменить Общий клиент' })).toBeNull()
    expect(list).toHaveBeenCalledWith(
      expect.objectContaining({ include_inactive: true, page: 1, limit: 20 }),
    )
  })

  it('searches by the entered query', async () => {
    render(<AdminClientsPage />)
    await screen.findByText('ООО Ромашка')
    const search = screen.getByPlaceholderText('КССС, ИНН или название')
    fireEvent.change(search, { target: { value: 'ромаш' } })
    fireEvent.keyDown(search, { key: 'Enter', code: 'Enter' })
    await waitFor(() => {
      expect(list).toHaveBeenCalledWith(expect.objectContaining({ q: 'ромаш', page: 1 }))
    })
  })
})
