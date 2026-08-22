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
      warehouse: { code: 2001, name: 'Склад Ростов' },
      quantity_requested: 1000,
      quantity_approved: 800,
      unit: 'шт',
      comment: null,
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
    expect(screen.getByText('Утверждено: 800')).toBeTruthy()
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
})
