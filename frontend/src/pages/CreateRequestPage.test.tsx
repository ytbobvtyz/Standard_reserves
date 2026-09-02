import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CreateRequestPage } from './CreateRequestPage'
import { useAuthStore } from '../stores/auth'

const getObjects = vi.fn()
const getProducts = vi.fn()
const getProduct = vi.fn()

vi.mock('../api/references', () => ({
  referencesApi: {
    getObjects: (...args: unknown[]) => getObjects(...args),
    getProducts: (...args: unknown[]) => getProducts(...args),
    getProduct: (...args: unknown[]) => getProduct(...args),
  },
}))

vi.mock('../api/requests', () => ({
  requestsApi: {
    create: vi.fn(),
    submit: vi.fn(),
  },
}))

const PALLET_HINT =
  /Пополнение возможно только кратно поддонной норме/

describe('CreateRequestPage', () => {
  beforeEach(() => {
    getObjects.mockReset()
    getProducts.mockReset()
    getProduct.mockReset()
    getObjects.mockResolvedValue({
      data: { status: 'success', data: [] },
    })
    getProducts.mockResolvedValue({
      data: { status: 'success', data: [] },
    })
    useAuthStore.setState({
      user: {
        id: '11111111-1111-1111-1111-111111111111',
        username: 'commercial',
        full_name: 'Иванов Иван',
        role: 'commercial',
      },
      token: 'token',
      isAuthenticated: true,
      isLoading: false,
    })
  })

  it('shows pallet hint for normative and one-time requests', async () => {
    render(
      <MemoryRouter>
        <CreateRequestPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Создать запрос')).toBeTruthy()
    })
    expect(screen.getByText(PALLET_HINT)).toBeTruthy()

    fireEvent.click(screen.getByRole('radio', { name: 'Разовое перемещение' }))
    expect(screen.getByText(PALLET_HINT)).toBeTruthy()
  })
})
