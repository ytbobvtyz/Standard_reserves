import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RequestDetailPage } from './RequestDetailPage'
import { useAuthStore } from '../stores/auth'
import type { RequestDetail } from '../api/types'

const getRequest = vi.fn()

vi.mock('../api/requests', () => ({
  requestsApi: {
    get: (...args: unknown[]) => getRequest(...args),
    submit: vi.fn(),
    remove: vi.fn(),
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
    getRequest.mockResolvedValue({ data: { status: 'success', data: request } })
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
})
