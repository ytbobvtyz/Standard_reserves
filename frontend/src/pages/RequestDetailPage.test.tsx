import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RequestDetailPage } from './RequestDetailPage'
import { useAuthStore } from '../stores/auth'
import type { RequestDetail } from '../api/types'

const getRequest = vi.fn()
const getHistory = vi.fn()
const removeRequest = vi.fn()
const updateExpiry = vi.fn()

vi.mock('../api/requests', () => ({
  requestsApi: {
    get: (...args: unknown[]) => getRequest(...args),
    getHistory: (...args: unknown[]) => getHistory(...args),
    submit: vi.fn(),
    remove: (...args: unknown[]) => removeRequest(...args),
    updateExpiry: (...args: unknown[]) => updateExpiry(...args),
  },
}))

const request: RequestDetail = {
  id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  request_type: 'normative',
  status: 'active',
  client_name: "ООО 'Ромашка'",
  initiator: {
    id: '11111111-1111-1111-1111-111111111111',
    username: 'commercial',
    full_name: 'Иванов Иван',
    role: 'commercial',
    department: 'Коммерческий отдел',
  },
  initiator_comment: null,
  comment_pp: 'Снижаем объем',
  comment_economy: 'Экономика приемлема',
  expiry_date: '2026-12-31',
  items: [
    {
      id: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
      product: {
        code: 10001,
        name: 'Подшипник 6204ZZ',
        category: 'A',
        weight_kg: 0.25,
      },
      warehouse: { code: 2001, name: 'Склад Ростов', long_distance: false },
      quantity_requested: 1000,
      quantity_approved: 800,
      unit: 'шт',
      comment: null,
      long_distance: false,
      requirement: 800,
    },
  ],
  history: [],
  created_at: '2026-08-18T09:00:00Z',
  updated_at: '2026-08-18T10:00:00Z',
}

describe('RequestDetailPage', () => {
  beforeEach(() => {
    getRequest.mockReset()
    getHistory.mockReset()
    removeRequest.mockReset()
    updateExpiry.mockReset()
    getRequest.mockResolvedValue({ data: { status: 'success', data: request } })
    getHistory.mockResolvedValue({
      data: {
        status: 'success',
        data: [
          {
            item_id: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
            field_name: 'quantity_approved',
            old_value: 1000,
            new_value: 800,
            changed_by: {
              id: '22222222-2222-2222-2222-222222222222',
              full_name: 'Петров Петр',
            },
            changed_at: '2026-08-18T09:30:00Z',
            comment: 'Снижаем объем на 20%',
          },
        ],
      },
    })
    useAuthStore.setState({
      user: request.initiator,
      token: 'token',
      isAuthenticated: true,
      isLoading: false,
    })
  })

  it('shows the final approved quantity', async () => {
    render(
      <MemoryRouter initialEntries={[`/requests/${request.id}`]}>
        <Routes>
          <Route path="/requests/:id" element={<RequestDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText("ООО 'Ромашка'")).toBeTruthy()
    })
    expect(screen.getByText('Иванов И. (Коммерческий отдел)')).toBeTruthy()
    expect(screen.getByText('Утверждено: 800')).toBeTruthy()
    expect(screen.getByText('A (×1,0)')).toBeTruthy()
    expect(screen.getByText('Нет (×1,0)')).toBeTruthy()
  })

  it('shows item change history on the history tab', async () => {
    render(
      <MemoryRouter initialEntries={[`/requests/${request.id}`]}>
        <Routes>
          <Route path="/requests/:id" element={<RequestDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText("ООО 'Ромашка'")).toBeTruthy()
    })
    fireEvent.click(screen.getByText('История изменений'))
    await waitFor(() => {
      expect(screen.getByText('Петров Петр')).toBeTruthy()
    })
    expect(screen.getByText('Утвержденное количество')).toBeTruthy()
    expect(screen.getByText('Снижаем объем на 20%')).toBeTruthy()
    expect(getHistory).toHaveBeenCalledWith(request.id)
  })

  it('hides delete and shows change-date for active requests', async () => {
    render(
      <MemoryRouter initialEntries={[`/requests/${request.id}`]}>
        <Routes>
          <Route path="/requests/:id" element={<RequestDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText("ООО 'Ромашка'")).toBeTruthy()
    })
    expect(screen.queryByRole('button', { name: 'Удалить' })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Изменить дату' }))
    expect(screen.getByRole('button', { name: 'Сохранить' })).toBeTruthy()
    expect(
      screen.getByText('Можно только уменьшить срок: от сегодня до текущей даты окончания'),
    ).toBeTruthy()
  })

  it('shows delete for draft requests', async () => {
    getRequest.mockResolvedValue({
      data: { status: 'success', data: { ...request, status: 'draft' } },
    })
    render(
      <MemoryRouter initialEntries={[`/requests/${request.id}`]}>
        <Routes>
          <Route path="/requests/:id" element={<RequestDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText("ООО 'Ромашка'")).toBeTruthy()
    })
    expect(screen.getByRole('button', { name: 'Удалить' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Изменить дату' })).toBeNull()
  })

  it('shows execution details and history for executed one-time requests', async () => {
    getRequest.mockResolvedValue({
      data: {
        status: 'success',
        data: {
          ...request,
          request_type: 'one_time',
          status: 'executed',
          expiry_date: null,
          order_number: 'РН-2026-08-20-001',
          executed_at: '2026-08-20T11:00:00Z',
          executed_comment: 'Отгрузка произведена',
          executed_by: {
            id: '44444444-4444-4444-4444-444444444444',
            username: 'logistics',
            full_name: 'Кузнецов Кузьма',
            role: 'logistics',
          },
          history: [
            {
              timestamp: '2026-08-18T09:00:00Z',
              action: 'created',
              user_name: 'Иванов Иван',
              comment: null,
            },
            {
              timestamp: '2026-08-20T11:00:00Z',
              action: 'executed',
              user_name: 'Кузнецов Кузьма',
              comment: 'Разнарядка: РН-2026-08-20-001. Отгрузка произведена',
            },
          ],
        },
      },
    })

    render(
      <MemoryRouter initialEntries={[`/requests/${request.id}`]}>
        <Routes>
          <Route path="/requests/:id" element={<RequestDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText("ООО 'Ромашка'")).toBeTruthy()
    })
    expect(screen.getByText('РН-2026-08-20-001')).toBeTruthy()
    expect(screen.getByText('Отгрузка произведена')).toBeTruthy()
    expect(screen.getByText(/Исполнен \(Кузнецов Кузьма\)/)).toBeTruthy()
    expect(screen.getByText('Разнарядка: РН-2026-08-20-001. Отгрузка произведена')).toBeTruthy()
  })

  it('hides category, distance and requirement columns for one-time requests', async () => {
    getRequest.mockResolvedValue({
      data: {
        status: 'success',
        data: {
          ...request,
          request_type: 'one_time',
          status: 'approved',
          expiry_date: null,
        },
      },
    })

    render(
      <MemoryRouter initialEntries={[`/requests/${request.id}`]}>
        <Routes>
          <Route path="/requests/:id" element={<RequestDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText("ООО 'Ромашка'")).toBeTruthy()
    })

    // Normative columns must not be present
    expect(screen.queryByText('Категория')).toBeNull()
    expect(screen.queryByText('Удалённость')).toBeNull()
    expect(screen.queryByText('Потребность')).toBeNull()
    expect(screen.queryByText('A (×1,0)')).toBeNull()
    expect(screen.queryByText('Нет (×1,0)')).toBeNull()

    // Base columns must be present
    expect(screen.getByText('Артикул')).toBeTruthy()
    expect(screen.getByText('Название')).toBeTruthy()
    expect(screen.getByText('Склад')).toBeTruthy()
    expect(screen.getByText('Количество')).toBeTruthy()
  })
})
