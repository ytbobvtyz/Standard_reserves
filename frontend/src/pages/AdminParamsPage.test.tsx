import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminParamsPage } from './AdminParamsPage'
import type { SystemParams } from '../api/types'

const params: SystemParams = {
  category_a: 1,
  category_b: 1.5,
  category_c: 2,
  remote_warehouse: 1.5,
  pallet_multiple: false,
  last_modified_by: {
    id: '44444444-4444-4444-4444-444444444444',
    username: 'logistics',
    full_name: 'Кузнецов Кузьма',
  },
  last_modified_at: '2026-09-15T06:00:00Z',
}

const getParams = vi.fn()
const updateParams = vi.fn()

vi.mock('../api/admin', () => ({
  adminApi: {
    getParams: (...args: unknown[]) => getParams(...args),
    updateParams: (...args: unknown[]) => updateParams(...args),
  },
}))

describe('AdminParamsPage', () => {
  beforeEach(() => {
    getParams.mockReset()
    updateParams.mockReset()
    getParams.mockResolvedValue({
      data: { status: 'success', data: params },
    })
    updateParams.mockResolvedValue({
      data: { status: 'success', data: { ...params, pallet_multiple: true } },
    })
  })

  it('renders coefficient fields and last change stamp', async () => {
    render(
      <MemoryRouter>
        <AdminParamsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Параметры')).toBeTruthy()
    })
    expect(screen.getByText('Категория A')).toBeTruthy()
    expect(screen.getByText('Категория B')).toBeTruthy()
    expect(screen.getByText('Категория C')).toBeTruthy()
    expect(screen.getByText('Удалённые склады')).toBeTruthy()
    expect(screen.getByText('Запросы кратно паллетной норме')).toBeTruthy()
    expect(screen.getByText(/logistics/)).toBeTruthy()
    expect(getParams).toHaveBeenCalled()
  })

  it('saves pallet toggle without coefficient confirmation', async () => {
    render(
      <MemoryRouter>
        <AdminParamsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Параметры')).toBeTruthy()
    })
    fireEvent.click(screen.getByRole('switch'))
    fireEvent.click(screen.getByRole('button', { name: 'Сохранить' }))
    await waitFor(() => {
      expect(updateParams).toHaveBeenCalled()
    })
    expect(
      screen.queryByText(/Вы меняете коэфициент категории/),
    ).toBeNull()
  })
})
