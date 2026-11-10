import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import dayjs from 'dayjs'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminAuditPage } from './AdminAuditPage'
import type { AuditEvent } from '../api/types'

const requestEvent: AuditEvent = {
  id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  created_at: '2026-11-10T14:32:05Z',
  user: {
    id: '11111111-1111-1111-1111-111111111111',
    full_name: 'Иванов Иван',
    role: 'commercial',
  },
  event_type: 'request_created',
  entity_type: 'request',
  entity_id: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
  entity_label: 'Запрос (ООО Ромашка)',
  details: { label: 'Запрос (ООО Ромашка)', status: 'draft' },
}

const productEvent: AuditEvent = {
  id: 'cccccccc-cccc-cccc-cccc-cccccccccccc',
  created_at: '2026-11-10T15:00:00Z',
  user: {
    id: '44444444-4444-4444-4444-444444444444',
    full_name: 'Кузнецов Кузьма',
    role: 'logistics',
  },
  event_type: 'product_updated',
  entity_type: 'product',
  entity_id: null,
  entity_label: 'Подшипник (10001)',
  details: { code: 10001, name: 'Подшипник', label: 'Подшипник (10001)' },
}

const objectEvent: AuditEvent = {
  id: 'dddddddd-dddd-dddd-dddd-dddddddddddd',
  created_at: '2026-11-10T16:00:00Z',
  user: null,
  event_type: 'object_created',
  entity_type: 'object',
  entity_id: null,
  entity_label: 'Склад (2001)',
  details: { code: 2001, label: 'Склад (2001)' },
}

const getAudit = vi.fn()
const getUsers = vi.fn()

vi.mock('../api/admin', () => ({
  adminApi: {
    getAudit: (...args: unknown[]) => getAudit(...args),
    getUsers: (...args: unknown[]) => getUsers(...args),
  },
}))

describe('AdminAuditPage', () => {
  beforeEach(() => {
    getAudit.mockReset()
    getUsers.mockReset()
    getUsers.mockResolvedValue({
      data: {
        status: 'success',
        data: [
          {
            id: '11111111-1111-1111-1111-111111111111',
            username: 'commercial',
            email: 'commercial@company.ru',
            full_name: 'Иванов Иван',
            role: 'commercial',
            is_active: true,
            created_at: '2026-11-01T00:00:00Z',
          },
        ],
      },
    })
    getAudit.mockResolvedValue({
      data: {
        status: 'success',
        data: [requestEvent, productEvent, objectEvent],
        meta: { page: 1, limit: 50, total: 3 },
      },
    })
  })

  it('loads today, links cards and expands details', async () => {
    render(
      <MemoryRouter>
        <AdminAuditPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('№bbbbbbbb Запрос (ООО Ромашка)')).toBeTruthy()
    })
    const today = dayjs().format('YYYY-MM-DD')
    expect(getAudit).toHaveBeenCalledWith(
      expect.objectContaining({
        date_from: today,
        date_to: today,
        page: 1,
        limit: 50,
      }),
    )
    expect(screen.getByText('Иванов Иван · Коммерция')).toBeTruthy()
    expect(screen.getByText('Создание запроса')).toBeTruthy()
    expect(
      screen.getByRole('link', { name: '№bbbbbbbb Запрос (ООО Ромашка)' }),
    ).toHaveProperty('getAttribute', expect.any(Function))
    expect(
      screen
        .getByRole('link', { name: '№bbbbbbbb Запрос (ООО Ромашка)' })
        .getAttribute('href'),
    ).toBe('/requests/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb')
    expect(screen.getByRole('link', { name: 'Подшипник (10001)' }).getAttribute('href')).toBe(
      '/references/products/10001',
    )
    expect(screen.getByText('Склад (2001)').closest('a')).toBeNull()
    expect(screen.getByText('Система')).toBeTruthy()

    fireEvent.click(screen.getAllByRole('button', { name: 'Expand row' })[0])
    await waitFor(() => {
      expect(screen.getByText(/"status": "draft"/)).toBeTruthy()
    })
  })

  it('applies the all-time preset', async () => {
    render(
      <MemoryRouter>
        <AdminAuditPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(getAudit).toHaveBeenCalled()
    })
    fireEvent.click(screen.getByRole('button', { name: 'Всё время' }))
    await waitFor(() => {
      expect(getAudit).toHaveBeenCalledWith(
        expect.objectContaining({
          date_from: '2020-01-01',
          date_to: dayjs().format('YYYY-MM-DD'),
        }),
      )
    })
  })

  it('sends the request number', async () => {
    render(
      <MemoryRouter>
        <AdminAuditPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(getAudit).toHaveBeenCalled()
    })
    fireEvent.change(screen.getByPlaceholderText('Номер запроса'), {
      target: { value: '№bbbbbbbb' },
    })
    await waitFor(() => {
      expect(getAudit).toHaveBeenCalledWith(
        expect.objectContaining({
          request_number: '№bbbbbbbb',
          page: 1,
        }),
      )
    })
  })
})
