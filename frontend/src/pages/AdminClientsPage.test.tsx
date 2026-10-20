import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminClientsPage } from './AdminClientsPage'
import type { ClientListItem } from '../api/types'

const list = vi.fn()
const remove = vi.fn()
const preview = vi.fn()
const upload = vi.fn()
const getDepartments = vi.fn()

vi.mock('../api/clients', () => ({
  clientsApi: {
    list: (...args: unknown[]) => list(...args),
    remove: (...args: unknown[]) => remove(...args),
    create: vi.fn(),
    update: vi.fn(),
    downloadTemplate: vi.fn(),
    exportExcel: vi.fn(),
    preview: (...args: unknown[]) => preview(...args),
    upload: (...args: unknown[]) => upload(...args),
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
    preview.mockReset()
    upload.mockReset()
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

  it('shows what the file will create and uploads after confirmation', async () => {
    preview.mockResolvedValue({
      data: {
        status: 'success',
        data: {
          file_rows: 3,
          to_create: 2,
          errors: 1,
          without_department: 0,
          departments: [
            {
              department_id: 'dept-1',
              department_name: 'АСТО (Направление продаж в АСТО)',
              count: 2,
            },
          ],
          message:
            'Будет создано 2 клиентов: АСТО (Направление продаж в АСТО) — 2. Не будут загружены 1 строк с ошибками',
          error_details: [{ row: 4, message: 'Подразделение «ОЕМ2» не найдено' }],
        },
      },
    })
    upload.mockResolvedValue({
      data: {
        status: 'success',
        data: {
          created: 2,
          errors: 1,
          message: 'Загружено 2 из 3',
          error_details: [{ row: 4, message: 'Подразделение «ОЕМ2» не найдено' }],
        },
      },
    })
    render(<AdminClientsPage />)
    await screen.findByText('ООО Ромашка')
    const file = new File(['data'], 'clients.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(input, { target: { files: [file] } })
    await waitFor(() => {
      const check = screen.getByRole('button', { name: 'Проверить файл' })
      expect((check as HTMLButtonElement).disabled).toBe(false)
    })
    fireEvent.click(screen.getByRole('button', { name: 'Проверить файл' }))
    expect(await screen.findByText(/Будет создано 2 клиентов/)).toBeTruthy()
    expect(screen.getByText('АСТО (Направление продаж в АСТО)')).toBeTruthy()
    expect(screen.getByText(/Строка 4: Подразделение «ОЕМ2» не найдено/)).toBeTruthy()
    expect(upload).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Загрузить 2' }))
    await waitFor(() => {
      expect(upload).toHaveBeenCalled()
    })
    expect(await screen.findByText(/Загружено 2, ошибок 1/)).toBeTruthy()
  })
})
