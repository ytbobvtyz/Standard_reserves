import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MyRequestsPage } from './MyRequestsPage'
import { useAuthStore } from '../stores/auth'
import type { RequestListItem } from '../api/types'

const listRequests = vi.fn()
const exportExcel = vi.fn()
const downloadBlob = vi.fn()

vi.mock('../api/requests', () => ({
  requestsApi: {
    list: (...args: unknown[]) => listRequests(...args),
    remove: vi.fn(),
    exportExcel: (...args: unknown[]) => exportExcel(...args),
  },
}))

vi.mock('../utils/download', () => ({
  downloadBlob: (...args: unknown[]) => downloadBlob(...args),
  filenameFromContentDisposition: () => 'requests_export_2026-10-27.xlsx',
}))

const requests: RequestListItem[] = [
  {
    id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    request_type: 'normative',
    status: 'draft',
    client_name: 'ООО Ромашка',
    initiator: {
      id: '11111111-1111-1111-1111-111111111111',
      username: 'commercial',
      full_name: 'Иванов Иван',
      role: 'commercial',
    },
    items_count: 1,
    total_quantity: 10,
    expiry_date: '2026-12-31',
    created_at: '2026-08-18T09:00:00Z',
  },
  {
    id: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
    request_type: 'one_time',
    status: 'rejected',
    client_name: 'ООО Тюльпан',
    initiator: {
      id: '11111111-1111-1111-1111-111111111111',
      username: 'commercial',
      full_name: 'Иванов Иван',
      role: 'commercial',
    },
    items_count: 2,
    total_quantity: 4,
    expiry_date: null,
    created_at: '2026-08-19T09:00:00Z',
  },
]

describe('MyRequestsPage', () => {
  beforeEach(() => {
    listRequests.mockReset()
    exportExcel.mockReset()
    downloadBlob.mockReset()
    listRequests.mockResolvedValue({
      data: { status: 'success', data: requests, meta: { page: 1, limit: 10, total: 2 } },
    })
    exportExcel.mockResolvedValue({
      data: new Blob(['xlsx']),
      headers: {},
    })
    useAuthStore.setState({
      user: requests[0].initiator,
      token: 'token',
      isAuthenticated: true,
      isLoading: false,
    })
  })

  it('exports the checked requests', async () => {
    render(
      <MemoryRouter>
        <MyRequestsPage />
      </MemoryRouter>,
    )

    const exportButton = await screen.findByRole('button', { name: /Выгрузить в Excel/ })
    expect(exportButton).toHaveProperty('disabled', true)

    fireEvent.click(await screen.findByRole('checkbox', { name: 'Выбрать запрос ООО Ромашка' }))
    fireEvent.click(screen.getByRole('checkbox', { name: 'Выбрать запрос ООО Тюльпан' }))
    expect(exportButton).toHaveProperty('disabled', false)

    fireEvent.click(exportButton)
    await waitFor(() => {
      expect(exportExcel).toHaveBeenCalledWith([
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
      ])
    })
    expect(downloadBlob).toHaveBeenCalled()
  })

  it('selects and clears every request with one checkbox', async () => {
    render(
      <MemoryRouter>
        <MyRequestsPage />
      </MemoryRouter>,
    )

    const selectAll = await screen.findByRole('checkbox', { name: 'Выбрать все' })
    fireEvent.click(selectAll)

    const first = screen.getByRole('checkbox', { name: 'Выбрать запрос ООО Ромашка' })
    const second = screen.getByRole('checkbox', { name: 'Выбрать запрос ООО Тюльпан' })
    expect((first as HTMLInputElement).checked).toBe(true)
    expect((second as HTMLInputElement).checked).toBe(true)
    expect((selectAll as HTMLInputElement).checked).toBe(true)

    fireEvent.click(selectAll)
    expect((first as HTMLInputElement).checked).toBe(false)
    expect((second as HTMLInputElement).checked).toBe(false)
    expect(screen.getByRole('button', { name: /Выгрузить в Excel/ })).toHaveProperty(
      'disabled',
      true,
    )
  })

  it('selects requests on other pages of the current filter', async () => {
    const thirdId = 'cccccccc-cccc-cccc-cccc-cccccccccccc'
    listRequests.mockImplementation(async (params?: { limit?: number }) => {
      if (params?.limit === 200) {
        return {
          data: {
            status: 'success',
            data: [
              ...requests,
              {
                ...requests[0],
                id: thirdId,
                client_name: 'ООО Василёк',
              },
            ],
            meta: { page: 1, limit: 200, total: 3 },
          },
        }
      }
      return {
        data: {
          status: 'success',
          data: requests,
          meta: { page: 1, limit: 10, total: 3 },
        },
      }
    })

    render(
      <MemoryRouter>
        <MyRequestsPage />
      </MemoryRouter>,
    )

    fireEvent.click(await screen.findByRole('checkbox', { name: 'Выбрать все' }))
    const exportButton = screen.getByRole('button', { name: /Выгрузить в Excel/ })
    await waitFor(() => {
      expect(exportButton).toHaveProperty('disabled', false)
    })
    fireEvent.click(exportButton)
    await waitFor(() => {
      expect(exportExcel).toHaveBeenCalledWith([
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        thirdId,
      ])
    })
  })
})
