import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { OneTimeRequestsPage } from './OneTimeRequestsPage'
import { useAuthStore } from '../stores/auth'
import type { OneTimeListItem } from '../api/types'

const approvedRequest: OneTimeListItem = {
  id: 'cccccccc-cccc-cccc-cccc-cccccccccccc',
  client_name: 'ООО «Тюльпан»',
  status: 'approved',
  initiator: {
    id: '11111111-1111-1111-1111-111111111111',
    username: 'commercial',
    full_name: 'Иванов Иван',
    role: 'commercial',
  },
  items: [
    {
      product_code: 10001,
      product_name: 'Подшипник 6204ZZ',
      warehouse_code: 2001,
      warehouse_name: 'Склад Ростов',
      quantity: 200,
      unit: 'шт',
    },
  ],
  created_at: '2026-08-18T09:00:00Z',
}

const executedRequest: OneTimeListItem = {
  ...approvedRequest,
  id: 'dddddddd-dddd-dddd-dddd-dddddddddddd',
  client_name: 'ООО «Бета»',
  status: 'executed',
  order_number: 'РН-2026-08-18-002',
}

const getOneTimeList = vi.fn()
const executeOneTime = vi.fn()
const getInitiators = vi.fn()
const getClients = vi.fn()
const exportOneTime = vi.fn()
const getObjects = vi.fn()

vi.mock('../api/logistics', () => ({
  logisticsApi: {
    getOneTimeList: (...args: unknown[]) => getOneTimeList(...args),
    executeOneTime: (...args: unknown[]) => executeOneTime(...args),
    getInitiators: (...args: unknown[]) => getInitiators(...args),
    getClients: (...args: unknown[]) => getClients(...args),
    exportOneTime: (...args: unknown[]) => exportOneTime(...args),
  },
}))

vi.mock('../api/references', () => ({
  referencesApi: {
    getObjects: (...args: unknown[]) => getObjects(...args),
  },
}))

describe('OneTimeRequestsPage', () => {
  beforeEach(() => {
    getOneTimeList.mockReset()
    executeOneTime.mockReset()
    getInitiators.mockReset()
    getClients.mockReset()
    exportOneTime.mockReset()
    getObjects.mockReset()
    URL.createObjectURL = vi.fn(() => 'blob:url')
    URL.revokeObjectURL = vi.fn()

    getOneTimeList.mockResolvedValue({
      data: {
        status: 'success',
        data: [approvedRequest, executedRequest],
        meta: { page: 1, limit: 10, total: 2 },
      },
    })
    getInitiators.mockResolvedValue({
      data: {
        status: 'success',
        data: [
          {
            id: '11111111-1111-1111-1111-111111111111',
            username: 'commercial',
            full_name: 'Иванов Иван',
          },
        ],
      },
    })
    getClients.mockResolvedValue({
      data: { status: 'success', data: ['ООО «Тюльпан»', 'ООО «Бета»'] },
    })
    getObjects.mockResolvedValue({
      data: {
        status: 'success',
        data: [{ code: 2001, name: 'Склад Ростов', city: 'Ростов', type: 'warehouse' }],
      },
    })
    executeOneTime.mockResolvedValue({
      data: {
        status: 'success',
        data: {
          id: approvedRequest.id,
          status: 'executed',
          executed_at: '2026-08-20T11:00:00Z',
          executed_by: '44444444-4444-4444-4444-444444444444',
          order_number: 'РН-2026-08-20-001',
          executed_comment: 'Отгрузка произведена',
        },
      },
    })
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
  })

  it('opens the one-time logistics page', async () => {
    render(
      <MemoryRouter>
        <OneTimeRequestsPage />
      </MemoryRouter>,
    )

    expect(screen.getAllByText('Разовые перемещения').length).toBeGreaterThan(0)
    await waitFor(() => {
      expect(screen.getByText('ООО «Тюльпан»')).toBeTruthy()
    })
    expect(screen.getByText('ООО «Бета»')).toBeTruthy()
    expect(screen.getAllByText('Иванов Иван').length).toBeGreaterThan(0)
    expect(getOneTimeList).toHaveBeenCalled()
  })

  it('applies client and status filters', async () => {
    render(
      <MemoryRouter>
        <OneTimeRequestsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('ООО «Тюльпан»')).toBeTruthy()
    })

    fireEvent.change(screen.getByRole('combobox', { name: 'Клиент' }), {
      target: { value: 'Тюльпан' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Применить фильтр' }))

    await waitFor(() => {
      expect(getOneTimeList).toHaveBeenCalledWith(
        expect.objectContaining({
          client_name: 'Тюльпан',
          page: 1,
          limit: 10,
        }),
      )
    })
  })

  it('opens execute modal and updates status after confirm', async () => {
    getOneTimeList
      .mockResolvedValueOnce({
        data: {
          status: 'success',
          data: [approvedRequest, executedRequest],
          meta: { page: 1, limit: 10, total: 2 },
        },
      })
      .mockResolvedValueOnce({
        data: {
          status: 'success',
          data: [
            { ...approvedRequest, status: 'executed', order_number: 'РН-2026-08-20-001' },
            executedRequest,
          ],
          meta: { page: 1, limit: 10, total: 2 },
        },
      })

    render(
      <MemoryRouter>
        <OneTimeRequestsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('ООО «Тюльпан»')).toBeTruthy()
    })

    fireEvent.click(screen.getByRole('button', { name: 'Исполнить' }))
    expect(screen.getByText(/Исполнить запрос №cccccccc/)).toBeTruthy()
    expect(screen.getByText('Номер разнарядки')).toBeTruthy()

    fireEvent.change(screen.getByPlaceholderText('РН-2026-08-20-001'), {
      target: { value: 'РН-2026-08-20-001' },
    })
    fireEvent.change(screen.getByPlaceholderText('Отгрузка произведена'), {
      target: { value: 'Отгрузка произведена' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Подтвердить' }))

    await waitFor(() => {
      expect(executeOneTime).toHaveBeenCalledWith(approvedRequest.id, {
        order_number: 'РН-2026-08-20-001',
        comment: 'Отгрузка произведена',
      })
    })
    await waitFor(() => {
      expect(getOneTimeList).toHaveBeenCalledTimes(2)
    })
  })
})
