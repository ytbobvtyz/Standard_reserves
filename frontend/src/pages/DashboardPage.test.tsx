import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DashboardPage } from './DashboardPage'
import { useAuthStore } from '../stores/auth'
import type {
  DashboardExceptionItem,
  DashboardSummary,
  DashboardTrendData,
  ExpiryCalendarData,
} from '../api/types'

const getSummary = vi.fn()
const getNormativeTrend = vi.fn()
const getExceptions = vi.fn()
const getWarehouseCoverage = vi.fn()
const getExpiryCalendar = vi.fn()
const getNzByDepartment = vi.fn()
const getTopClients = vi.fn()
const getProducts = vi.fn()
const getProduct = vi.fn()
const getObjects = vi.fn()
const getDepartments = vi.fn()
const listClients = vi.fn()
const getClient = vi.fn()

vi.mock('../api/dashboard', () => ({
  dashboardApi: {
    getSummary: (...args: unknown[]) => getSummary(...args),
    getNormativeTrend: (...args: unknown[]) => getNormativeTrend(...args),
    getExceptions: (...args: unknown[]) => getExceptions(...args),
    getWarehouseCoverage: (...args: unknown[]) => getWarehouseCoverage(...args),
    getExpiryCalendar: (...args: unknown[]) => getExpiryCalendar(...args),
    getNzByDepartment: (...args: unknown[]) => getNzByDepartment(...args),
    getTopClients: (...args: unknown[]) => getTopClients(...args),
  },
}))

vi.mock('../api/references', () => ({
  referencesApi: {
    getProducts: (...args: unknown[]) => getProducts(...args),
    getProduct: (...args: unknown[]) => getProduct(...args),
    getObjects: (...args: unknown[]) => getObjects(...args),
    getDepartments: (...args: unknown[]) => getDepartments(...args),
  },
}))

vi.mock('../api/clients', () => ({
  clientsApi: {
    list: (...args: unknown[]) => listClients(...args),
    get: (...args: unknown[]) => getClient(...args),
  },
}))

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: unknown }) => (
    <div>{children as never}</div>
  ),
  BarChart: ({
    data,
    onClick,
    children,
  }: {
    data: Array<{ period?: string; warehouse?: string }>
    onClick?: (state: { activeLabel: string }) => void
      children: unknown
  }) => (
    <div>
      {data.map((row, index) => (
        <button
          key={row.period ?? row.warehouse ?? String(index)}
          type="button"
          onClick={() => onClick?.({ activeLabel: row.period ?? '' })}
        >
          столбец {row.period ?? row.warehouse}
        </button>
      ))}
      {children}
    </div>
  ),
  Bar: () => null,
  Cell: () => null,
  CartesianGrid: () => null,
  Legend: () => null,
  Tooltip: () => null,
  Brush: () => null,
  XAxis: () => null,
  YAxis: () => null,
}))

const summary: DashboardSummary = {
  active_count: 1245,
  active_quantity: 1.5,
  deficit_quantity: 0.1,
  coverage_pct: 93.33,
  coverage_with_transfers: 93.33,
  coverage_available_only: 80,
  expiring_30d: 12,
  expiring_30d_quantity: 0.25,
  avg_remaining_days: 45,
  unit: 'т',
}

const trend: DashboardTrendData = {
  group_by: 'week',
  date_from: '2026-09-01',
  date_to: '2026-09-16',
  unit: 'т',
  periods: ['2026-09-01', '2026-09-08'],
  series: [
    {
      key: 'warehouse:2001',
      warehouse_code: 2001,
      warehouse_name: 'Ростов',
      points: [
        { period: '2026-09-01', total_normative: 1000, count_active: 1 },
        { period: '2026-09-08', total_normative: 800, count_active: 1 },
      ],
    },
  ],
}

const exceptions: DashboardExceptionItem[] = [
  {
    product_code: 10001,
    product_name: 'Подшипник',
    warehouse_code: 2001,
    warehouse_name: 'Ростов',
    normative_quantity: 1000,
    requirement: 1000,
    available: 600,
    plan: 600,
    deficit: 400,
    unit: 'т',
    status: 'critical',
    request_id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  },
]

const calendar: ExpiryCalendarData = {
  date_from: '2026-09-16',
  date_to: '2026-09-20',
  unit: 'т',
  days: [{ date: '2026-09-20', count: 2, quantity: 0.1 }],
}

function renderPage() {
  useAuthStore.setState({
    user: {
      id: '1',
      username: 'logistics',
      full_name: 'Кузнецов Кузьма',
      role: 'logistics',
    },
    token: 'token',
    isAuthenticated: true,
    isLoading: false,
  })
  return render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <Routes>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/requests/:id" element={<div>Карточка запроса</div>} />
        <Route path="/logistics/dashboard" element={<div>Логистика</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('DashboardPage', () => {
  beforeEach(() => {
    getSummary.mockResolvedValue({ data: { data: summary } })
    getNormativeTrend.mockResolvedValue({ data: { data: trend } })
    getExceptions.mockResolvedValue({ data: { data: exceptions, meta: { page: 1, limit: 20, total: 21 } } })
    getWarehouseCoverage.mockResolvedValue({
      data: {
        data: {
          unit: 'т',
          warehouses: [
            {
              warehouse_code: 2001,
              warehouse_name: 'Ростов',
              normative_quantity: 1,
              available: 2,
              planned: 0.5,
              deficit: 0.4,
              requirement: 1,
              coverage_pct: 60,
              mismatch: true,
              unit: 'т',
            },
          ],
        },
      },
    })
    getExpiryCalendar.mockResolvedValue({ data: { data: calendar } })
    getNzByDepartment.mockResolvedValue({
      data: {
        data: {
          unit: 'т',
          items: [
            {
              department_id: null,
              department_name: 'Без управления',
              warehouses: [
                { warehouse_code: 2001, warehouse_name: 'Ростов', nz_quantity: 1.5 },
              ],
            },
          ],
        },
      },
    })
    getTopClients.mockResolvedValue({
      data: {
        data: {
          unit: 'т',
          items: [
            {
              client_id: 'c1',
              client_code: 7701000001,
              client_name: 'ООО Ромашка',
              inn: '7701000001',
              department_name: null,
              nz_quantity: 1.5,
            },
          ],
        },
      },
    })
    getProducts.mockResolvedValue({ data: { data: [{ code: 10001, name: 'Подшипник' }] } })
    getObjects.mockResolvedValue({
      data: { data: [{ code: 2001, name: 'Ростов' }] },
    })
    getDepartments.mockResolvedValue({
      data: {
        data: [{ id: 'dept-1', name: 'Коммерческий отдел', is_active: true }],
      },
    })
    getProduct.mockResolvedValue({
      data: { data: { code: 10001, name: 'Подшипник', is_active: true } },
    })
    listClients.mockResolvedValue({
      data: {
        data: [
          {
            id: 'c-romashka',
            client_code: 7701000001,
            name: 'ООО Ромашка',
            inn: '7701000001',
            is_active: true,
            is_system: false,
          },
        ],
      },
    })
    getClient.mockResolvedValue({
      data: {
        data: {
          id: 'c-romashka',
          client_code: 7701000001,
          name: 'ООО Ромашка',
          inn: '7701000001',
          is_active: true,
          is_system: false,
        },
      },
    })
  })

  it('renders north star, chart, exceptions and heatmap', async () => {
    renderPage()
    expect(await screen.findByText('Дашборд нормативов')).toBeTruthy()
    expect(screen.getByText('Активных НЗ')).toBeTruthy()
    expect(screen.getByText('1,500')).toBeTruthy()
    expect(screen.getByText('0,100')).toBeTruthy()
    expect(screen.getByText('0,250')).toBeTruthy()
    expect(screen.getByText('Покрытие с учётом перемещений')).toBeTruthy()
    expect(screen.getByText('Покрытие доступным стоком')).toBeTruthy()
    expect(screen.queryByText('Средний срок')).toBeNull()
    expect(getDepartments).toHaveBeenCalledWith({ has_normatives: true })
    expect(screen.getByText('Динамика нормативов')).toBeTruthy()
    expect(screen.getByText('Текущее покрытие по складам')).toBeTruthy()
    expect(screen.getByText('Требуют внимания')).toBeTruthy()
    expect(screen.getByText(/ещё 20 скрыто/)).toBeTruthy()
    expect(screen.getByText('НЗ в разрезе управлений продаж')).toBeTruthy()
    expect(screen.getByText('Топ-10 клиентов по объёму НЗ')).toBeTruthy()
    expect(screen.getByText('Календарь истечений')).toBeTruthy()
    expect(screen.getByText('10001')).toBeTruthy()
    expect(screen.getByText('Критично')).toBeTruthy()
    expect(screen.queryByText('Заказ')).toBeNull()
    expect(
      screen.getByText(/Покрытие с учётом перемещений = \(общий НЗ/),
    ).toBeTruthy()
    expect(screen.getByText(/излишняя/)).toBeTruthy()
  })

  it('reloads all widgets when warehouse changes', async () => {
    renderPage()
    await screen.findByText('Дашборд нормативов')
    const warehouseSelect = screen.getByTestId('warehouse-filter').querySelector('.ant-select-selector')
    expect(warehouseSelect).toBeTruthy()
    fireEvent.mouseDown(warehouseSelect as Element)
    fireEvent.click(await screen.findByText('2001 · Ростов'))
    await waitFor(() => {
      expect(getSummary).toHaveBeenCalledWith(
        expect.objectContaining({ warehouse_code: 2001 }),
      )
      expect(getNormativeTrend).toHaveBeenCalledWith(
        expect.objectContaining({ warehouse_code: 2001 }),
      )
      expect(getExceptions).toHaveBeenCalledWith(
        expect.objectContaining({ warehouse_code: 2001 }),
      )
      expect(getWarehouseCoverage).toHaveBeenCalledWith(
        expect.objectContaining({ warehouse_code: 2001 }),
      )
      expect(getExpiryCalendar).toHaveBeenCalledWith(
        expect.objectContaining({ warehouse_code: 2001 }),
      )
      expect(getNzByDepartment).toHaveBeenCalledWith({
        unit: 'т',
        warehouse_code: 2001,
      })
      expect(getTopClients).toHaveBeenCalledWith({
        unit: 'т',
        limit: 10,
        warehouse_code: 2001,
      })
    })
  })

  it('reloads all widgets when department changes', async () => {
    renderPage()
    await screen.findByText('Дашборд нормативов')
    const departmentSelect = screen
      .getByTestId('department-filter')
      .querySelector('.ant-select-selector')
    expect(departmentSelect).toBeTruthy()
    fireEvent.mouseDown(departmentSelect as Element)
    fireEvent.click(await screen.findByText('Коммерческий отдел'))
    await waitFor(() => {
      expect(getSummary).toHaveBeenCalledWith(
        expect.objectContaining({ department_id: 'dept-1' }),
      )
      expect(getNormativeTrend).toHaveBeenCalledWith(
        expect.objectContaining({ department_id: 'dept-1' }),
      )
      expect(getExceptions).toHaveBeenCalledWith(
        expect.objectContaining({ department_id: 'dept-1' }),
      )
      expect(getWarehouseCoverage).toHaveBeenCalledWith(
        expect.objectContaining({ department_id: 'dept-1' }),
      )
      expect(getExpiryCalendar).toHaveBeenCalledWith(
        expect.objectContaining({ department_id: 'dept-1' }),
      )
      expect(getNzByDepartment).toHaveBeenCalledWith({
        unit: 'т',
        department_id: 'dept-1',
      })
      expect(getTopClients).toHaveBeenCalledWith({
        unit: 'т',
        limit: 10,
        department_id: 'dept-1',
      })
    })
  })

  it('searches any product and filters the trend by client', async () => {
    renderPage()
    await screen.findByText('Дашборд нормативов')
    const productInput = screen.getByTestId('product-filter').querySelector('input')
    expect(productInput).toBeTruthy()
    fireEvent.change(productInput as HTMLInputElement, { target: { value: '99999' } })
    await waitFor(() => {
      expect(getProducts).toHaveBeenCalledWith(
        expect.objectContaining({ search: '99999', is_active: true }),
      )
    })

    const clientSelect = screen.getByTestId('client-filter').querySelector('.ant-select-selector')
    expect(clientSelect).toBeTruthy()
    fireEvent.mouseDown(clientSelect as Element)
    fireEvent.click(await screen.findByText('7701000001 — ООО Ромашка'))
    await waitFor(() => {
      expect(getNormativeTrend).toHaveBeenCalledWith(
        expect.objectContaining({ client_id: 'c-romashka' }),
      )
    })
  })

  it('reloads dashboard when mass unit changes', async () => {
    renderPage()
    await screen.findByText('Дашборд нормативов')
    fireEvent.click(screen.getByRole('radio', { name: 'кг' }))
    await waitFor(() => {
      expect(getSummary).toHaveBeenCalledWith({ unit: 'кг' })
      expect(getNzByDepartment).toHaveBeenCalledWith({ unit: 'кг' })
      expect(getTopClients).toHaveBeenCalledWith({ unit: 'кг', limit: 10 })
      expect(getNormativeTrend).toHaveBeenCalledWith(
        expect.objectContaining({ unit: 'кг' }),
      )
    })
  })

  it('reloads trend when period changes', async () => {
    renderPage()
    await screen.findByText('Дашборд нормативов')
    const periodSelect = screen.getByTestId('period-select').querySelector('.ant-select-selector')
    expect(periodSelect).toBeTruthy()
    fireEvent.mouseDown(periodSelect as Element)
    fireEvent.click(await screen.findByText('Месяц'))
    await waitFor(() => {
      expect(getNormativeTrend).toHaveBeenCalledWith(
        expect.objectContaining({ group_by: 'month' }),
      )
    })
  })

  it('drills down when a chart bar is clicked', async () => {
    renderPage()
    await screen.findByText('столбец 2026-09-01')
    fireEvent.click(screen.getByText('столбец 2026-09-01'))
    expect(await screen.findByText(/Фильтр по дате/)).toBeTruthy()
    expect(screen.getByText('Все артикулы')).toBeTruthy()
  })

  it('opens request card from exception row', async () => {
    renderPage()
    await screen.findByText('10001')
    fireEvent.click(screen.getByText('10001'))
    expect(await screen.findByText('Карточка запроса')).toBeTruthy()
  })
})
