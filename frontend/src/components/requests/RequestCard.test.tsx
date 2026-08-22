import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { RequestCard } from './RequestCard'
import type { RequestListItem } from '../../api/types'

const baseRequest: RequestListItem = {
  id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  request_type: 'normative',
  status: 'draft',
  client_name: "ООО 'Ромашка'",
  initiator: {
    id: '11111111-1111-1111-1111-111111111111',
    username: 'commercial',
    full_name: 'Иванов Иван',
    role: 'commercial',
  },
  items_count: 1,
  total_quantity: 1000,
  expiry_date: '2026-12-31',
  created_at: '2026-08-18T09:00:00Z',
}

describe('RequestCard', () => {
  it('shows delete for deletable statuses', () => {
    const onDelete = vi.fn()
    render(
      <MemoryRouter>
        <RequestCard request={baseRequest} canDelete onDelete={onDelete} />
      </MemoryRouter>,
    )
    expect(screen.getByRole('button', { name: 'Удалить' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Удалить' }))
    expect(screen.getByText('Вы уверены, что хотите удалить запрос?')).toBeTruthy()
  })

  it('hides delete for active, approved and executed', () => {
    for (const status of ['active', 'approved', 'executed'] as const) {
      const { unmount } = render(
        <MemoryRouter>
          <RequestCard request={{ ...baseRequest, status }} />
        </MemoryRouter>,
      )
      expect(screen.queryByRole('button', { name: 'Удалить' })).toBeNull()
      unmount()
    }
  })
})
