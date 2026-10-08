import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import dayjs from 'dayjs'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CreateRequestPage, MONTHLY_QUANTITY_HINT } from './CreateRequestPage'
import { DEFAULT_EXPIRY_HINT } from '../utils/expiryDate'
import { useAuthStore } from '../stores/auth'

const getObjects = vi.fn()
const getProducts = vi.fn()
const getProduct = vi.fn()
const getParams = vi.fn()

vi.mock('../api/references', () => ({
  referencesApi: {
    getObjects: (...args: unknown[]) => getObjects(...args),
    getProducts: (...args: unknown[]) => getProducts(...args),
    getProduct: (...args: unknown[]) => getProduct(...args),
    getParams: (...args: unknown[]) => getParams(...args),
  },
}))

vi.mock('../api/requests', () => ({
  requestsApi: {
    create: vi.fn(),
    submit: vi.fn(),
  },
}))

const PALLET_HINT =
  'В настоящее время запросы на нормативный запас/разовое перемещение принимаются только кратно поддонной норме'

describe('CreateRequestPage', () => {
  beforeEach(() => {
    getObjects.mockReset()
    getProducts.mockReset()
    getProduct.mockReset()
    getParams.mockReset()
    getObjects.mockResolvedValue({
      data: { status: 'success', data: [] },
    })
    getProducts.mockResolvedValue({
      data: { status: 'success', data: [] },
    })
    getParams.mockResolvedValue({
      data: {
        status: 'success',
        data: {
          category_a: 1,
          category_b: 1.5,
          category_c: 2,
          remote_warehouse: 1.5,
          pallet_multiple: false,
        },
      },
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

  it('hides pallet hint when pallet_multiple is off', async () => {
    render(
      <MemoryRouter>
        <CreateRequestPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(getParams).toHaveBeenCalled()
    })
    expect(screen.queryByText(PALLET_HINT)).toBeNull()
  })

  it('shows pallet hint for normative and one-time requests when pallet_multiple is on', async () => {
    getParams.mockResolvedValue({
      data: {
        status: 'success',
        data: {
          category_a: 1,
          category_b: 1.5,
          category_c: 2,
          remote_warehouse: 1.5,
          pallet_multiple: true,
        },
      },
    })
    render(
      <MemoryRouter>
        <CreateRequestPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText(PALLET_HINT)).toBeTruthy()
    })

    fireEvent.click(screen.getByRole('radio', { name: 'Разовое перемещение' }))
    expect(screen.getByText(PALLET_HINT)).toBeTruthy()
  })

  it('shows category, distance and requirement columns for normative and hides them for one-time', async () => {
    render(
      <MemoryRouter>
        <CreateRequestPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Создать запрос')).toBeTruthy()
    })

    // Initially normative
    expect(screen.getByText('Категория')).toBeTruthy()
    expect(screen.getByText('Удалённость')).toBeTruthy()
    expect(screen.getByText('Потребность')).toBeTruthy()

    // Switch to one-time
    fireEvent.click(screen.getByRole('radio', { name: 'Разовое перемещение' }))
    expect(screen.queryByText('Категория')).toBeNull()
    expect(screen.queryByText('Удалённость')).toBeNull()
    expect(screen.queryByText('Потребность')).toBeNull()

    // Switch back to normative
    fireEvent.click(screen.getByRole('radio', { name: 'Нормативный' }))
    expect(screen.getByText('Категория')).toBeTruthy()
    expect(screen.getByText('Удалённость')).toBeTruthy()
    expect(screen.getByText('Потребность')).toBeTruthy()
  })

  it('prefills normative expiry at three months and explains the default', async () => {
    render(
      <MemoryRouter>
        <CreateRequestPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText(DEFAULT_EXPIRY_HINT)).toBeTruthy()
    })
    expect(
      screen.getByDisplayValue(dayjs().add(3, 'month').format('YYYY-MM-DD')),
    ).toBeTruthy()
  })

  it('renames quantity to monthly amount and shows the hint for normative requests', async () => {
    render(
      <MemoryRouter>
        <CreateRequestPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Количество в месяц')).toBeTruthy()
    })

    fireEvent.mouseOver(screen.getByLabelText('Что такое количество в месяц'))
    await waitFor(() => {
      expect(screen.getByRole('tooltip').textContent).toContain(MONTHLY_QUANTITY_HINT)
    })

    fireEvent.click(screen.getByRole('radio', { name: 'Разовое перемещение' }))
    expect(screen.queryByText('Количество в месяц')).toBeNull()
    expect(screen.getByText('Кол-во')).toBeTruthy()
  })
})
