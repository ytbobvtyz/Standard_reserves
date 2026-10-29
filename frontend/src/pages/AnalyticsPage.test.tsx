import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import dayjs from 'dayjs'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defaultStockRange } from '../components/analytics/stockDynamics'
import { AnalyticsPage } from './AnalyticsPage'

const getStockDynamics = vi.fn()
const getStockBounds = vi.fn()
const getStockSummary = vi.fn()
const getProducts = vi.fn()
const getProduct = vi.fn()
const getObjects = vi.fn()
const getDepartments = vi.fn()
const listClients = vi.fn()
const getClient = vi.fn()

vi.mock('../api/analytics', () => ({
  analyticsApi: {
    getStockDynamics: (...args: unknown[]) => getStockDynamics(...args),
    getStockBounds: (...args: unknown[]) => getStockBounds(...args),
    getStockSummary: (...args: unknown[]) => getStockSummary(...args),
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
  ResponsiveContainer: ({ children }: { children: unknown }) => <div>{children as never}</div>,
  ComposedChart: ({ children }: { children: unknown }) => <div>{children as never}</div>,
  Bar: ({ name }: { name: string }) => <div>{name}</div>,
  Line: ({ name }: { name: string }) => <div>{name}</div>,
  CartesianGrid: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  Brush: () => null,
}))

const summary = {
  status: 'success',
  data: {
    unit: 'т',
    months: [
      {
        month: '2026-08-01',
        available_median: null,
        actual: null,
        normative_avg: null,
      },
      {
        month: '2026-09-01',
        available_median: 4,
        actual: 2,
        normative_avg: 11,
      },
      {
        month: '2026-10-01',
        available_median: 8,
        actual: 4,
        normative_avg: 16,
      },
    ],
  },
}

const series = {
  status: 'success',
  data: {
    dates: ['2026-10-01', '2026-11-01'],
    normative: [10, 12],
    available_min: [4, 5],
    available_median: [8, 7],
    available_max: [10, 9],
    actual: [1, 2],
    unit: 'т',
  },
}

describe('AnalyticsPage', () => {
  beforeEach(() => {
    getStockDynamics.mockReset()
    getStockBounds.mockReset()
    getStockSummary.mockReset()
    getProducts.mockResolvedValue({
      data: {
        status: 'success',
        data: [{ code: 10001, name: 'Масло', category: 'A', is_active: true }],
      },
    })
    getProduct.mockResolvedValue({
      data: { status: 'success', data: { code: 10001, name: 'Масло', category: 'A' } },
    })
    getObjects.mockResolvedValue({ data: { status: 'success', data: [] } })
    getDepartments.mockResolvedValue({ data: { status: 'success', data: [] } })
    listClients.mockResolvedValue({ data: { status: 'success', data: [] } })
    getClient.mockResolvedValue({ data: { status: 'success', data: null } })
    getStockDynamics.mockResolvedValue({ data: series })
    getStockBounds.mockResolvedValue({
      data: { status: 'success', data: { earliest_date: '2024-03-01' } },
    })
    getStockSummary.mockResolvedValue({ data: summary })
  })

  it('asks for a product and does not request the chart', async () => {
    render(<AnalyticsPage />)
    expect(screen.getByText('Аналитика запасов')).toBeTruthy()
    expect(screen.getByText('Выберите продукт')).toBeTruthy()
    await waitFor(() => {
      expect(getDepartments).toHaveBeenCalledWith({ has_normatives: true })
    })
    expect(getStockDynamics).not.toHaveBeenCalled()
    expect(getStockSummary).not.toHaveBeenCalled()
  })

  it('loads monthly dynamics by default and shows stock bands with period sales', async () => {
    render(<AnalyticsPage />)
    fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Продукт' }))
    fireEvent.click(await screen.findByText('10001 — Масло'))

    await waitFor(() => {
      expect(getStockBounds).toHaveBeenCalledWith(
        expect.objectContaining({ product_code: 10001 }),
      )
      expect(getStockDynamics).toHaveBeenCalledWith(
        expect.objectContaining({
          product_code: 10001,
          granularity: 'month',
          date_from: '2024-03-01',
        }),
      )
    })
    const legend = await screen.findByTestId('stock-legend')
    expect(legend.textContent).toContain('Норматив')
    expect(legend.textContent).toContain('Мин. остаток')
    expect(legend.textContent).toContain('Медиана остатка')
    expect(legend.textContent).toContain('Макс. остаток')
    expect(legend.textContent).toContain('Реализация')
    expect(legend.textContent).not.toContain('накопл')
    await waitFor(() => {
      expect(getStockSummary).toHaveBeenCalledWith(
        expect.objectContaining({ product_code: 10001 }),
      )
    })
    expect(screen.getByText('Сводка за последние 6 месяцев')).toBeTruthy()
    const table = screen.getByTestId('stock-summary')
    expect(table.textContent).toContain('Медианный остаток, т')
    expect(table.textContent).toContain('Реализация, т')
    expect(table.textContent).toContain('Средний норматив, т')
    expect(table.textContent).toContain('16')
    expect(table.textContent).toContain('—')
    expect(table.textContent).toContain('Среднее')
    expect(table.textContent).toContain('13,5')
  })

  it('switches the period to a year for weeks and to 90 days for days', async () => {
    render(<AnalyticsPage />)
    fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Продукт' }))
    fireEvent.click(await screen.findByText('10001 — Масло'))
    await waitFor(() => expect(getStockDynamics).toHaveBeenCalled())

    fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Гранулярность' }))
    fireEvent.click(await screen.findByText('Неделя'))
    const year = defaultStockRange('week', dayjs())
    await waitFor(() => {
      expect(getStockDynamics).toHaveBeenCalledWith(
        expect.objectContaining({
          granularity: 'week',
          date_from: year.from,
          date_to: year.to,
        }),
      )
    })

    fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Гранулярность' }))
    fireEvent.click(await screen.findByText('День'))
    const days = defaultStockRange('day', dayjs())
    await waitFor(() => {
      expect(getStockDynamics).toHaveBeenCalledWith(
        expect.objectContaining({
          granularity: 'day',
          date_from: days.from,
          date_to: days.to,
        }),
      )
    })
  })

  it('shows an empty chart when the period has no normatives', async () => {
    getStockDynamics.mockResolvedValue({
      data: {
        status: 'success',
        data: {
          dates: ['2026-10-01'],
          normative: [null],
          available_min: [1],
          available_median: [1],
          available_max: [1],
          actual: [1],
          unit: 'т',
        },
      },
    })
    render(<AnalyticsPage />)
    fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Продукт' }))
    fireEvent.click(await screen.findByText('10001 — Масло'))
    expect(await screen.findByText('Нет данных за период')).toBeTruthy()
  })
})
