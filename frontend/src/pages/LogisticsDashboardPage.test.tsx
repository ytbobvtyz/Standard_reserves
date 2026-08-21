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
          available: 600,
          plan: 600,
          unit: 'шт',
          deficit: 400,
          client_name: "ООО 'Ромашка'",
          expiry_date: '2026-12-31',
          status: 'warning',
          stock_unit: 'ШТ',
        },
      ],
    },
    {
      warehouse_code: 2003,
      warehouse_name: 'Склад Казань',
      total_deficit: 80,
      deficit_count: 1,
      deficit_items: [
        {
          product_code: 10003,
          product_name: 'Вал приводной 500мм',
          category: 'C',
          normative_quantity: 120,
          available: 40,
          plan: 40,
          unit: 'шт',
          deficit: 80,
          client_name: "ООО 'Ромашка'",
          expiry_date: '2026-12-31',
          status: 'warning',
          stock_unit: 'КГ',
        },
      ],
    },
  ],
  summary: {
    total_deficit: 480,
    deficit_warehouses: 2,
    deficit_products: 2,
  },
}

const getDashboard = vi.fn()
const generateOrders = vi.fn()
const generateOrdersBulk = vi.fn()
const exportOrders = vi.fn()
const uploadBalances = vi.fn()
const getObjects = vi.fn()

vi.mock('../api/logistics', () => ({
  logisticsApi: {
    getDashboard: (...args: unknown[]) => getDashboard(...args),
    generateOrders: (...args: unknown[]) => generateOrders(...args),
    generateOrdersBulk: (...args: unknown[]) => generateOrdersBulk(...args),
    exportOrders: (...args: unknown[]) => exportOrders(...args),
    uploadBalances: (...args: unknown[]) => uploadBalances(...args),
  },
}))

vi.mock('../api/references', () => ({
  referencesApi: {
    getObjects: (...args: unknown[]) => getObjects(...args),
  },
}))

function setRole(role: 'logistics' | 'commercial') {
  useAuthStore.setState({
    user: {
      id: '44444444-4444-4444-4444-444444444444',
      username: role,
      full_name: role === 'logistics' ? 'Кузнецов Кузьма' : 'Иванов Иван',
      role,
    },
    token: 'token',
    isAuthenticated: true,
    isLoading: false,
  })
}

describe('LogisticsDashboardPage', () => {
  beforeEach(() => {
    getDashboard.mockReset()
    generateOrders.mockReset()
    generateOrdersBulk.mockReset()
    exportOrders.mockReset()
    uploadBalances.mockReset()
    getObjects.mockReset()
    getDashboard.mockResolvedValue({ data: dashboard })
    getObjects.mockResolvedValue({
      data: {
        status: 'success',
        data: [
          { code: 2001, name: 'Склад Ростов', city: 'Ростов', type: 'warehouse' },
          { code: 2003, name: 'Склад Казань', city: 'Казань', type: 'warehouse' },
        ],
      },
    })
    generateOrdersBulk.mockResolvedValue({
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
    setRole('logistics')
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
    expect(screen.getAllByText('Доступно').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Запланировано').length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: /Загрузить актуальные остатки/ })).toBeTruthy()
    expect(screen.getAllByText("ООО 'Ромашка'").length).toBeGreaterThan(0)
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
      expect(generateOrdersBulk).toHaveBeenCalledWith({
        warehouse_codes: [2001, 2003],
      })
    })
    await waitFor(() => {
      expect(screen.getByText('Сформировать заказы')).toBeTruthy()
      expect(screen.getByText(/Завод Московский/)).toBeTruthy()
      expect(screen.getByRole('button', { name: /Подтвердить/ })).toBeTruthy()
      expect(screen.getByRole('button', { name: /Скачать Excel/ })).toBeTruthy()
    })
  })

  it('keeps selected orders button disabled until a warehouse is checked', async () => {
    render(
      <MemoryRouter>
        <LogisticsDashboardPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Склад Ростов')).toBeTruthy()
    })
    expect(
      screen.getByRole('button', { name: /Сформировать заказы на выбранные склады/ }),
    ).toHaveProperty('disabled', true)

    fireEvent.click(screen.getByRole('checkbox', { name: 'Выбрать Склад Ростов' }))
    expect(
      screen.getByRole('button', { name: /Сформировать заказы на выбранные склады/ }),
    ).toHaveProperty('disabled', false)

    fireEvent.click(
      screen.getByRole('button', { name: /Сформировать заказы на выбранные склады/ }),
    )
    await waitFor(() => {
      expect(generateOrdersBulk).toHaveBeenCalledWith({
        warehouse_codes: [2001],
      })
    })
  })

  it('selects all visible warehouses', async () => {
    render(
      <MemoryRouter>
        <LogisticsDashboardPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Склад Казань')).toBeTruthy()
    })
    fireEvent.click(screen.getByRole('checkbox', { name: 'Выбрать все склады' }))
    expect(
      screen.getByRole('checkbox', { name: 'Выбрать Склад Ростов' }),
    ).toHaveProperty('checked', true)
    expect(
      screen.getByRole('checkbox', { name: 'Выбрать Склад Казань' }),
    ).toHaveProperty('checked', true)

    fireEvent.click(
      screen.getByRole('button', { name: /Сформировать заказы на выбранные склады/ }),
    )
    await waitFor(() => {
      expect(generateOrdersBulk).toHaveBeenCalledWith({
        warehouse_codes: [2001, 2003],
      })
    })
  })

  it('hides management buttons for commercial and keeps data visible', async () => {
    setRole('commercial')
    render(
      <MemoryRouter>
        <LogisticsDashboardPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Склад Ростов')).toBeTruthy()
    })
    expect(screen.getByText('Подшипник 6204ZZ')).toBeTruthy()
    expect(
      screen.queryByRole('button', { name: /Сформировать заказы/ }),
    ).toBeNull()
    expect(screen.queryByRole('button', { name: /Скачать Excel/ })).toBeNull()
    expect(
      screen.queryByRole('button', { name: /Загрузить актуальные остатки/ }),
    ).toBeNull()
    expect(screen.queryByRole('checkbox', { name: 'Выбрать все склады' })).toBeNull()
  })

  it('opens upload modal and shows report', async () => {
    uploadBalances.mockResolvedValue({
      data: {
        status: 'success',
        data: {
          uploaded: 1,
          created: 0,
          updated: 1,
          errors: 1,
          message: 'Загружено 1, ошибок 1',
          error_details: [{ row: 3, message: 'Склад ERP X999 не найден' }],
        },
      },
    })
    render(
      <MemoryRouter>
        <LogisticsDashboardPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Склад Ростов')).toBeTruthy()
    })
    fireEvent.click(screen.getByRole('button', { name: /Загрузить актуальные остатки/ }))
    expect(screen.getByText(/Перетащите Excel-файл/)).toBeTruthy()

    const file = new File(['data'], 'balances.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(input, { target: { files: [file] } })

    await waitFor(() => {
      expect(uploadBalances).toHaveBeenCalled()
    })
    await waitFor(() => {
      expect(screen.getByText('Загружено 1, ошибок 1')).toBeTruthy()
    })
    expect(screen.getByText(/Строка 3/)).toBeTruthy()
  }, 15000)
})
