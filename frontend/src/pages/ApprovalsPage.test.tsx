import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApprovalsPage } from './ApprovalsPage'
import { useAuthStore } from '../stores/auth'
import type { ApprovalPendingRequest } from '../api/types'

const pendingRequest: ApprovalPendingRequest = {
  id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  request_type: 'normative',
  client_name: "ООО 'Ромашка'",
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
      quantity_requested: 1000,
      quantity_approved: null,
      unit: 'шт',
    },
  ],
  expiry_date: '2026-12-31',
  created_at: '2026-08-18T09:00:00Z',
}

const getPPPending = vi.fn()
const ppAction = vi.fn()
const getEconomyPending = vi.fn()
const economyAction = vi.fn()

vi.mock('../api/approvals', () => ({
  approvalsApi: {
    getPPPending: (...args: unknown[]) => getPPPending(...args),
    ppAction: (...args: unknown[]) => ppAction(...args),
    getEconomyPending: (...args: unknown[]) => getEconomyPending(...args),
    economyAction: (...args: unknown[]) => economyAction(...args),
  },
}))

describe('ApprovalsPage', () => {
  beforeEach(() => {
    getPPPending.mockReset()
    ppAction.mockReset()
    getEconomyPending.mockReset()
    economyAction.mockReset()
    getPPPending.mockResolvedValue({
      data: {
        status: 'success',
        data: [pendingRequest],
        meta: { page: 1, limit: 50, total: 1 },
      },
    })
    ppAction.mockResolvedValue({
      data: {
        status: 'success',
        data: {
          id: pendingRequest.id,
          status: 'economy_check',
          pp_action: 'approve',
        },
      },
    })
    useAuthStore.setState({
      user: {
        id: '22222222-2222-2222-2222-222222222222',
        username: 'pp',
        full_name: 'Петров Петр',
        role: 'pp',
      },
      token: 'token',
      isAuthenticated: true,
      isLoading: false,
    })
  })

  it('shows pending list for PP', async () => {
    render(
      <MemoryRouter initialEntries={['/approvals/pp']}>
        <ApprovalsPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Согласование ПП')).toBeTruthy()
    await waitFor(() => {
      expect(screen.getByText("ООО 'Ромашка'")).toBeTruthy()
    })
    expect(getPPPending).toHaveBeenCalled()
  })

  it('opens approval modal with items', async () => {
    render(
      <MemoryRouter initialEntries={['/approvals/pp']}>
        <ApprovalsPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText("ООО 'Ромашка'")).toBeTruthy()
    })
    fireEvent.click(screen.getByRole('button', { name: 'Открыть' }))
    expect(screen.getByText(/Согласование запроса №aaaaaaaa/)).toBeTruthy()
    expect(screen.getByText('Подшипник 6204ZZ')).toBeTruthy()
    expect(screen.getByText('Склад Ростов')).toBeTruthy()
    expect(screen.getByText('Срок действия')).toBeTruthy()
    expect(
      screen.getByText('Минимальный срок — 3 месяца, максимальный — 6 месяцев'),
    ).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Утвердить' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Редактировать' })).toBeNull()
    expect(screen.getByRole('button', { name: 'Отказать' })).toBeTruthy()

    // Normative columns are present
    expect(screen.getByText('Категория')).toBeTruthy()
    expect(screen.getByText('Удалённость')).toBeTruthy()
    expect(screen.getByText('Потребность')).toBeTruthy()
  })

  it('hides category, distance and requirement columns for one-time requests in modal', async () => {
    const oneTimeRequest: ApprovalPendingRequest = {
      ...pendingRequest,
      id: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
      request_type: 'one_time',
      expiry_date: null,
    }
    getPPPending.mockResolvedValue({
      data: {
        status: 'success',
        data: [oneTimeRequest],
        meta: { page: 1, limit: 50, total: 1 },
      },
    })

    render(
      <MemoryRouter initialEntries={['/approvals/pp']}>
        <ApprovalsPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText("ООО 'Ромашка'")).toBeTruthy()
    })
    fireEvent.click(screen.getByRole('button', { name: 'Открыть' }))
    expect(screen.getByText(/Согласование запроса №bbbbbbbb/)).toBeTruthy()

    // Base columns must be present
    expect(screen.getByText('Артикул')).toBeTruthy()
    expect(screen.getByText('Название')).toBeTruthy()
    expect(screen.getByText('Склад')).toBeTruthy()
    expect(screen.getByText('Запрос')).toBeTruthy()
    expect(screen.getByText('Количество')).toBeTruthy()
    expect(screen.getByText('Ед')).toBeTruthy()

    // Coefficient and requirement columns must NOT be present
    expect(screen.queryByText('Категория')).toBeNull()
    expect(screen.queryByText('Удалённость')).toBeNull()
    expect(screen.queryByText('Потребность')).toBeNull()
  })

  it('shows decrease-only expiry hint for economist', async () => {
    getEconomyPending.mockResolvedValue({
      data: {
        status: 'success',
        data: [pendingRequest],
        meta: { page: 1, limit: 50, total: 1 },
      },
    })
    useAuthStore.setState({
      user: {
        id: '33333333-3333-3333-3333-333333333333',
        username: 'economist',
        full_name: 'Сидоров Сидор',
        role: 'economist',
      },
      token: 'token',
      isAuthenticated: true,
      isLoading: false,
    })

    render(
      <MemoryRouter initialEntries={['/approvals/economy']}>
        <ApprovalsPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText("ООО 'Ромашка'")).toBeTruthy()
    })
    fireEvent.click(screen.getByRole('button', { name: 'Открыть' }))
    expect(screen.getByText('Срок действия')).toBeTruthy()
    expect(
      screen.getByText(
        'Срок можно только уменьшить: не раньше 3 месяцев от даты создания и не позже текущей даты',
      ),
    ).toBeTruthy()
  })

  it('approves a request and refreshes the list', async () => {
    getPPPending
      .mockResolvedValueOnce({
        data: {
          status: 'success',
          data: [pendingRequest],
          meta: { page: 1, limit: 50, total: 1 },
        },
      })
      .mockResolvedValueOnce({
        data: {
          status: 'success',
          data: [],
          meta: { page: 1, limit: 50, total: 0 },
        },
      })

    render(
      <MemoryRouter initialEntries={['/approvals/pp']}>
        <ApprovalsPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText("ООО 'Ромашка'")).toBeTruthy()
    })
    fireEvent.click(screen.getByRole('button', { name: 'Открыть' }))
    fireEvent.click(screen.getByRole('button', { name: 'Утвердить' }))

    await waitFor(() => {
      expect(ppAction).toHaveBeenCalledWith(pendingRequest.id, {
        action: 'approve',
        comment: undefined,
        items: [
          {
            product_code: 10001,
            warehouse_code: 2001,
            quantity_approved: 1000,
          },
        ],
        expiry_date: '2026-12-31',
      })
    })
    await waitFor(() => {
      expect(getPPPending).toHaveBeenCalledTimes(2)
    })
  })

  it('shows previously approved quantity in the modal', async () => {
    getPPPending.mockResolvedValue({
      data: {
        status: 'success',
        data: [
          {
            ...pendingRequest,
            items: [
              {
                ...pendingRequest.items[0],
                quantity_approved: 800,
              },
            ],
          },
        ],
        meta: { page: 1, limit: 50, total: 1 },
      },
    })

    render(
      <MemoryRouter initialEntries={['/approvals/pp']}>
        <ApprovalsPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText("ООО 'Ромашка'")).toBeTruthy()
    })
    fireEvent.click(screen.getByRole('button', { name: 'Открыть' }))
    expect(screen.getByDisplayValue('800')).toBeTruthy()
  })
})
