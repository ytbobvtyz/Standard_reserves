import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ClientAnalyticsData } from '../api/types'
import { defaultStockRange } from '../components/analytics/stockDynamics'
import { ClientAnalyticsPage } from './ClientAnalyticsPage'
import dayjs from 'dayjs'

const getClientAnalytics = vi.fn()
const getParams = vi.fn()
const listClients = vi.fn()
const getClient = vi.fn()

vi.mock('../api/analytics', () => ({
  analyticsApi: {
    getClientAnalytics: (...args: unknown[]) => getClientAnalytics(...args),
  },
}))

vi.mock('../api/references', () => ({
  referencesApi: {
    getParams: (...args: unknown[]) => getParams(...args),
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

const CLIENT_ID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'

const payload: ClientAnalyticsData = {
  client_id: CLIENT_ID,
  client_name: 'ООО Ромашка',
  department_name: 'Коммерческий отдел',
  is_system: false,
  chart: {
    dates: ['2026-06-01'],
    normative: [2.4],
    actual: [6],
    unit: 'т',
  },
  slice: {
    normative_tons: 2.4,
    avg_monthly_tons: 1.2,
    period_tons: 6,
    coverage_months: 2,
    outside_normative: false,
  },
  warehouses: [
    {
      code: 2001,
      name: 'Склад Ростов',
      normative_tons: 2.4,
      avg_monthly_tons: 1.2,
      period_tons: 6,
      coverage_months: 2,
      outside_normative: false,
    },
  ],
  products: [
    {
      code: 10001,
      name: 'Подшипник',
      normative_tons: 2.4,
      avg_monthly_tons: 1.2,
      period_tons: 6,
      coverage_months: 2,
      outside_normative: false,
      related: [],
    },
    {
      code: 10002,
      name: 'Старый подшипник',
      normative_tons: 0,
      avg_monthly_tons: 0.4,
      period_tons: 1,
      coverage_months: 0,
      outside_normative: true,
      related: [],
    },
  ],
  unmatched: [
    {
      loading_point: 'Z711',
      avg_monthly_tons: 0.2,
      period_tons: 1,
      coverage_months: 0,
      outside_normative: true,
    },
  ],
}

function renderPage(path = `/analytics/client/${CLIENT_ID}`) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/analytics/client" element={<ClientAnalyticsPage />} />
        <Route path="/analytics/client/:clientId" element={<ClientAnalyticsPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ClientAnalyticsPage', () => {
  beforeEach(() => {
    getClientAnalytics.mockReset()
    getParams.mockReset()
    listClients.mockReset()
    getClient.mockReset()
    getParams.mockResolvedValue({
      data: { data: { coverage_high_months: 2, coverage_low_months: 4 } },
    })
    listClients.mockResolvedValue({ data: { data: [] } })
    getClient.mockResolvedValue({
      data: {
        data: {
          id: CLIENT_ID,
          client_code: 7701000001,
          inn: '7701000001',
          name: 'ООО Ромашка',
          is_active: true,
          is_system: false,
        },
      },
    })
    getClientAnalytics.mockResolvedValue({ data: { data: payload } })
  })

  it('asks for a client before loading the chart', () => {
    renderPage('/analytics/client')
    expect(screen.getByText('Выберите клиента')).toBeTruthy()
    expect(getClientAnalytics).not.toHaveBeenCalled()
  })

  it('highlights consumption that has no normative and keeps an unmatched point', async () => {
    renderPage()
    expect(await screen.findByText('Нет в нормативе')).toBeTruthy()
    expect(screen.getByText('Z711')).toBeTruthy()
    expect(screen.getByText('10002 Старый подшипник')).toBeTruthy()
    const range = defaultStockRange('month', dayjs())
    await waitFor(() => {
      expect(getClientAnalytics).toHaveBeenCalledWith(
        CLIENT_ID,
        expect.objectContaining({
          date_from: range.from,
          date_to: range.to,
          granularity: 'month',
          include_related: true,
        }),
      )
    })
  })

  it('reloads without related sales when the switch is turned off', async () => {
    renderPage()
    await screen.findByText('Нет в нормативе')
    fireEvent.click(screen.getByRole('checkbox', { name: 'Учитывать родственные артикулы в покрытии' }))
    await waitFor(() => {
      expect(getClientAnalytics).toHaveBeenLastCalledWith(
        CLIENT_ID,
        expect.objectContaining({ include_related: false }),
      )
    })
  })

  it('hides the chart when every article is cleared', async () => {
    renderPage()
    await screen.findByText('Нет в нормативе')
    fireEvent.click(screen.getByRole('checkbox', { name: 'Все артикулы' }))
    expect(await screen.findByText('Отметьте хотя бы один склад и один артикул')).toBeTruthy()
    await waitFor(() => {
      expect(getClientAnalytics).toHaveBeenLastCalledWith(
        CLIENT_ID,
        expect.objectContaining({ product_codes: [] }),
      )
    })
  })
})
