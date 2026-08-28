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
          requirement: 1000,
          available: 600,
          plan: 600,
          unit: 'шт',
          deficit: 400,
          client_name: "ООО 'Ромашка'",
          expiry_date: '2026-12-31',
          status: 'warning',
          stock_unit: 'ШТ',
          weight_kg: 0.25,
        },
        {
          product_code: 10002,
          product_name: 'Корпус без дефицита',
          category: 'B',
          normative_quantity: 500,
          requirement: 500,
          available: 500,
          plan: 500,
          unit: 'шт',
          deficit: 0,
          client_name: "ООО 'Ромашка'",
          expiry_date: '2026-12-31',
          status: 'ok',
          stock_unit: 'ШТ',
          weight_kg: 2.5,
        },
      ],
    },
    {
      warehouse_code: 2003,
      warehouse_name: 'Склад Казань',
      long_distance: true,
      long_distance_message:
        'Ввиду удалённого расположения склада, пополнение возможно по железной дороге — срок доставки около 1 месяца от даты готовности продукции на производственной площадке, в связи с чем нормативы увеличены',
      total_deficit: 80,
      deficit_count: 1,
      deficit_items: [
        {
          product_code: 10003,
          product_name: 'Вал приводной 500мм',
          category: 'C',
          normative_quantity: 120,
          requirement: 120,
          available: 40,
          plan: 40,
          unit: 'шт',
          deficit: 80,
          client_name: "ООО 'Ромашка'",
          expiry_date: '2026-12-31',
          status: 'warning',
          stock_unit: 'КГ',
          weight_kg: 1,
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
const exportB2B = vi.fn()
const uploadBalances = vi.fn()
const getSyncInfo = vi.fn()
const getObjects = vi.fn()

vi.mock('../api/logistics', () => ({
  logisticsApi: {
    getDashboard: (...args: unknown[]) => getDashboard(...args),
    generateOrders: (...args: unknown[]) => generateOrders(...args),
    generateOrdersBulk: (...args: unknown[]) => generateOrdersBulk(...args),
    exportOrders: (...args: unknown[]) => exportOrders(...args),
    exportB2B: (...args: unknown[]) => exportB2B(...args),
    uploadBalances: (...args: unknown[]) => uploadBalances(...args),
    getSyncInfo: (...args: unknown[]) => getSyncInfo(...args),
  },
}))

const downloadBlob = vi.fn()

vi.mock('../utils/download', () => ({
  downloadBlob: (...args: unknown[]) => downloadBlob(...args),
  filenameFromContentDisposition: (header?: string) => {
    if (!header) {
      return null
    }
    const match = /filename="?([^";]+)"?/i.exec(header)
    return match?.[1] ?? null
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

async function expandWarehouse(name: string) {
  await waitFor(() => {
    expect(screen.getByText(name)).toBeTruthy()
  })
  fireEvent.click(screen.getByText(name))
  await waitFor(() => {
    expect(document.querySelector('.ant-collapse-item-active')).toBeTruthy()
  })
}

describe('LogisticsDashboardPage', () => {
  beforeEach(() => {
    getDashboard.mockReset()
    generateOrders.mockReset()
    generateOrdersBulk.mockReset()
    exportOrders.mockReset()
    exportB2B.mockReset()
    downloadBlob.mockReset()
    uploadBalances.mockReset()
    getSyncInfo.mockReset()
    getObjects.mockReset()
    getDashboard.mockResolvedValue({ data: dashboard })
    getSyncInfo.mockResolvedValue({
      data: {
        status: 'success',
        data: {
          last_balances_sync_at: '2026-08-22T14:30:00+05:00',
          last_balances_sync_by: {
            id: '44444444-4444-4444-4444-444444444444',
            username: 'ivanov',
            full_name: 'Иванов Иван',
            role: 'logistics',
          },
        },
      },
    })
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
                  weight_kg: 0.25,
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
    exportB2B.mockResolvedValue({
      data: new Blob(['zip']),
      headers: { 'content-disposition': 'attachment; filename="b2b_orders_20260828.zip"' },
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
      expect(screen.getByText(/Актуальные остатки обновлены/)).toBeTruthy()
      expect(screen.getByText(/Иванов И\. \(logistics\)/)).toBeTruthy()
    })
    await expandWarehouse('Склад Ростов')
    expect(screen.getByText('Подшипник 6204ZZ')).toBeTruthy()
    expect(screen.getByText('Корпус без дефицита')).toBeTruthy()
    expect(screen.getByRole('columnheader', { name: 'Категория' })).toBeTruthy()
    expect(screen.getByText('A')).toBeTruthy()
    expect(screen.getByText('B')).toBeTruthy()
    expect(screen.getAllByText('Потребность').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Доступно').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Запланировано').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/норматив:/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/доступно:/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/запланировано:/).length).toBeGreaterThan(0)
    expect(screen.getByText(/Всего норматив:/)).toBeTruthy()
    expect(screen.getByText(/Всего доступно:/)).toBeTruthy()
    expect(screen.getByText(/Всего запланировано:/)).toBeTruthy()
    expect(screen.getByRole('button', { name: /Загрузить актуальные остатки/ })).toBeTruthy()
    expect(screen.getAllByText("ООО 'Ромашка'").length).toBeGreaterThan(0)
    expect(getDashboard).toHaveBeenCalledTimes(1)
    expect(getDashboard).toHaveBeenCalledWith({
      unit: 'шт',
      filter_mode: 'all',
    })
    expect(getSyncInfo).toHaveBeenCalled()
  })

  it('converts units on the client without refetching', async () => {
    render(
      <MemoryRouter>
        <LogisticsDashboardPage />
      </MemoryRouter>,
    )
    await expandWarehouse('Склад Ростов')
    expect(screen.getByText('Подшипник 6204ZZ')).toBeTruthy()
    fireEvent.click(screen.getByRole('radio', { name: 'тонны' }))
    await waitFor(() => {
      expect(screen.getAllByText('0,25').length).toBeGreaterThan(0)
    })
    expect(getDashboard).toHaveBeenCalledTimes(1)
    expect(getDashboard).toHaveBeenCalledWith({
      unit: 'шт',
      filter_mode: 'all',
    })
  })

  it('filters on the client without refetching', async () => {
    render(
      <MemoryRouter>
        <LogisticsDashboardPage />
      </MemoryRouter>,
    )
    await expandWarehouse('Склад Ростов')
    expect(screen.getByText('Корпус без дефицита')).toBeTruthy()
    fireEvent.click(screen.getByRole('radio', { name: 'Требуют пополнения' }))
    await waitFor(() => {
      expect(screen.queryByText('Корпус без дефицита')).toBeNull()
    })
    expect(screen.getByText('Подшипник 6204ZZ')).toBeTruthy()
    expect(getDashboard).toHaveBeenCalledTimes(1)
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
      expect(screen.getByText('📦 Предпросмотр заказов')).toBeTruthy()
      expect(screen.getByText(/Завод Московский/)).toBeTruthy()
      expect(screen.getByRole('checkbox', { name: 'Выбрать все маршруты' })).toBeTruthy()
      expect(screen.getByRole('button', { name: /Подтвердить/ })).toBeTruthy()
      expect(screen.getByRole('button', { name: /Выгрузить для B2B/ })).toBeTruthy()
    })
  })

  it('downloads a B2B zip for selected routes', async () => {
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
      expect(screen.getByRole('button', { name: /Выгрузить для B2B/ })).toBeTruthy()
    })
    fireEvent.click(screen.getByRole('button', { name: /Выгрузить для B2B/ }))
    await waitFor(() => {
      expect(exportB2B).toHaveBeenCalledWith({
        routes: [
          {
            plant_code: 1001,
            plant_name: 'Завод Московский',
            warehouse_code: 2001,
            warehouse_name: 'Склад Ростов',
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
      })
    })
    expect(downloadBlob).toHaveBeenCalled()
    expect(downloadBlob.mock.calls[0][1]).toBe('b2b_orders_20260828.zip')
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
    await expandWarehouse('Склад Ростов')
    expect(screen.getByText('Подшипник 6204ZZ')).toBeTruthy()
    expect(
      screen.queryByRole('button', { name: /Сформировать заказы/ }),
    ).toBeNull()
    expect(screen.queryByRole('button', { name: /Скачать Excel/ })).toBeNull()
    expect(
      screen.queryByRole('button', { name: /Загрузить актуальные остатки/ }),
    ).toBeNull()
    expect(screen.queryByRole('checkbox', { name: 'Выбрать все склады' })).toBeNull()
    expect(screen.getByText(/Актуальные остатки обновлены/)).toBeTruthy()
    expect(screen.getByText(/Иванов И\. \(logistics\)/)).toBeTruthy()
  })

  it('shows a notice for a remote warehouse', async () => {
    render(
      <MemoryRouter>
        <LogisticsDashboardPage />
      </MemoryRouter>,
    )
    await expandWarehouse('Склад Казань')
    expect(screen.getByText('Удалённый')).toBeTruthy()
    expect(screen.getByText('Удалённый склад')).toBeTruthy()
    expect(
      screen.getByText(/пополнение возможно по железной дороге/),
    ).toBeTruthy()
    expect(screen.getByRole('columnheader', { name: 'Категория' })).toBeTruthy()
    expect(screen.getByText('C')).toBeTruthy()
  })

  it('shows empty sync message when balances were never uploaded', async () => {
    getSyncInfo.mockResolvedValue({
      data: {
        status: 'success',
        data: {
          last_balances_sync_at: null,
          last_balances_sync_by: null,
        },
      },
    })
    render(
      <MemoryRouter>
        <LogisticsDashboardPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Актуальные остатки ещё не загружались')).toBeTruthy()
    })
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
