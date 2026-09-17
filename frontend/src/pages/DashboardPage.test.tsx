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
const getProducts = vi.fn()
const getObjects = vi.fn()

vi.mock('../api/dashboard', () => ({
  dashboardApi: {
    getSummary: (...args: unknown[]) => getSummary(...args),
    getNormativeTrend: (...args: unknown[]) => getNormativeTrend(...args),
    getExceptions: (...args: unknown[]) => getExceptions(...args),
    getWarehouseCoverage: (...args: unknown[]) => getWarehouseCoverage(...args),
    getExpiryCalendar: (...args: unknown[]) => getExpiryCalendar(...args),
  },
}))

vi.mock('../api/references', () => ({
  referencesApi: {
    getProducts: (...args: unknown[]) => getProducts(...args),
    getObjects: (...args: unknown[]) => getObjects(...args),
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
  CartesianGrid: () => null,
  Legend: () => null,
  Tooltip: () => null,
  Brush: () => null,
  XAxis: () => null,
  YAxis: () => null,
}))

const summary: DashboardSummary = {
  active_count: 1245,
  deficit_quantity: 0.1,
  coverage_pct: 87,
  expiring_30d: 12,
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
    getProducts.mockResolvedValue({ data: { data: [{ code: 10001, name: 'Подшипник' }] } })
    getObjects.mockResolvedValue({
      data: { data: [{ code: 2001, name: 'Ростов' }] },
    })
  })

  it('renders north star, chart, exceptions and heatmap', async () => {
    renderPage()
    expect(await screen.findByText('Дашборд нормативов')).toBeTruthy()
    expect(screen.getByText('Активных НЗ')).toBeTruthy()
    expect(screen.getByText('Динамика нормативов')).toBeTruthy()
    expect(screen.getByText('Текущее покрытие по складам')).toBeTruthy()
    expect(screen.getByText('Требуют внимания')).toBeTruthy()
    expect(screen.getByText(/ещё 20 скрыто/)).toBeTruthy()
    expect(screen.getByText('Календарь истечений')).toBeTruthy()
    expect(screen.getByText('10001')).toBeTruthy()
    expect(screen.getByText('Критично')).toBeTruthy()
    expect(screen.queryByText('Заказ')).toBeNull()
    expect(
      screen.getByText(/Покрытие — доля потребности в нормативе запаса/),
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
    })
  })

  it('reloads dashboard when mass unit changes', async () => {
    renderPage()
    await screen.findByText('Дашборд нормативов')
    fireEvent.click(screen.getByRole('radio', { name: 'кг' }))
    await waitFor(() => {
      expect(getSummary).toHaveBeenCalledWith({ unit: 'кг' })
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
