import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LogisticsDashboardPage } from './LogisticsDashboardPage'
import { useAuthStore } from '../stores/auth'
import type { LogisticsDashboardData } from '../api/types'

const dashboard: LogisticsDashboardData = {
  status: 'success',
  data: [
    {
      warehouse_code: 2001,
      warehouse_name: 'Склад Ростов',
      total_deficit: 400,
      deficit_count: 1,
      deficit_items: [
        {
          product_code: 10001,
          product_name: 'Подшипник 6204ZZ',
          category: 'A',
          normative_quantity: 1000,
          fact_quantity: 600,
          unit: 'шт',
          deficit: 400,
          client_name: "ООО 'Ромашка'",
          expiry_date: '2026-12-31',
          status: 'warning',
        },
      ],
    },
  ],
  summary: {
    total_deficit: 400,
    deficit_warehouses: 1,
    deficit_products: 1,
  },
}

const getDashboard = vi.fn()
const generateOrders = vi.fn()
const exportOrders = vi.fn()
const getObjects = vi.fn()

vi.mock('../api/logistics', () => ({
  logisticsApi: {
    getDashboard: (...args: unknown[]) => getDashboard(...args),
    generateOrders: (...args: unknown[]) => generateOrders(...args),
    exportOrders: (...args: unknown[]) => exportOrders(...args),
  },
}))

vi.mock('../api/references', () => ({
  referencesApi: {
    getObjects: (...args: unknown[]) => getObjects(...args),
  },
}))

describe('LogisticsDashboardPage', () => {
  beforeEach(() => {
    getDashboard.mockReset()
    generateOrders.mockReset()
    exportOrders.mockReset()
    getObjects.mockReset()
    getDashboard.mockResolvedValue({ data: dashboard })
    getObjects.mockResolvedValue({
      data: {
        status: 'success',
        data: [{ code: 2001, name: 'Склад Ростов', city: 'Ростов', type: 'warehouse' }],
      },
    })
    generateOrders.mockResolvedValue({
      data: {
        status: 'success',
        data: {
          orders: [
            {
              plant_code: 1001,
              plant_name: 'Завод Московский',
              warehouse_code: 2001,
              warehouse_name: 'Склад Ростов',
              estimated_delivery_days: 5,
              items: [
                {
                  product_code: 10001,
                  product_name: 'Подшипник 6204ZZ',
                  deficit: 400,
                  unit: 'шт',
                },
              ],
            },
          ],
          total_orders: 1,
          total_products: 1,
          total_quantity: 400,
        },
      },
    })
    useAuthStore.setState({
      user: {
        id: '44444444-4444-4444-4444-444444444444',
        username: 'logistics',
        full_name: 'Кузнецов Кузьма',
        role: 'logistics',
      },
      token: 'token',
      isAuthenticated: true,
      isLoading: false,
    })
  })

  it('shows warehouses grouped with deficit items', async () => {
    render(
      <MemoryRouter>
        <LogisticsDashboardPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Дашборд логиста')).toBeTruthy()
    await waitFor(() => {
      expect(screen.getByText('Склад Ростов')).toBeTruthy()
    })
    expect(screen.getByText('Подшипник 6204ZZ')).toBeTruthy()
    expect(screen.getByText("ООО 'Ромашка'")).toBeTruthy()
    expect(getDashboard).toHaveBeenCalled()
  })

  it('refetches dashboard when unit toggle changes', async () => {
    render(
      <MemoryRouter>
        <LogisticsDashboardPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Склад Ростов')).toBeTruthy()
    })
    fireEvent.click(screen.getByRole('radio', { name: 'тонны' }))
    await waitFor(() => {
      expect(getDashboard).toHaveBeenCalledWith(
        expect.objectContaining({ unit: 'т' }),
      )
    })
  })

  it('refetches dashboard when filter changes', async () => {
    render(
      <MemoryRouter>
        <LogisticsDashboardPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Склад Ростов')).toBeTruthy()
    })
    fireEvent.click(screen.getByRole('radio', { name: 'Требуют пополнения' }))
    await waitFor(() => {
      expect(getDashboard).toHaveBeenCalledWith(
        expect.objectContaining({ filter_mode: 'deficit_only' }),
      )
    })
  })

  it('opens generate orders modal', async () => {
    render(
      <MemoryRouter>
        <LogisticsDashboardPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Склад Ростов')).toBeTruthy()
    })
    fireEvent.click(
      screen.getByRole('button', { name: /Сформировать заказы на все склады/ }),
    )
    await waitFor(() => {
      expect(generateOrders).toHaveBeenCalledWith(2001)
    })
    await waitFor(() => {
      expect(screen.getByText('Сформировать заказы')).toBeTruthy()
      expect(screen.getByText(/Завод Московский/)).toBeTruthy()
      expect(screen.getByRole('button', { name: /Подтвердить/ })).toBeTruthy()
      expect(screen.getByRole('button', { name: /Скачать Excel/ })).toBeTruthy()
    })
  })
})
