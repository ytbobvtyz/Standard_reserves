import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import dayjs from 'dayjs'
import { BalanceHistoryPage } from './BalanceHistoryPage'
import type { BalanceHistoryItem } from '../api/types'

const row: BalanceHistoryItem = {
  id: 'hist-1',
  snapshot_date: '2026-10-27',
  snapshot_at: '2026-10-27T09:00:00Z',
  warehouse_code: 2001,
  warehouse_name: 'Склад Ростов',
  product_code: 10001,
  product_name: 'Подшипник',
  available: 10,
  plan: 12,
  unit: 'ШТ',
  source: 'excel_upload',
  created_at: '2026-10-27T09:00:00Z',
}

const getBalanceHistory = vi.fn()
const getBalanceSnapshotDates = vi.fn()
const getObjects = vi.fn()
const getProducts = vi.fn()
const getProduct = vi.fn()

vi.mock('../api/logistics', () => ({
  logisticsApi: {
    getBalanceHistory: (...args: unknown[]) => getBalanceHistory(...args),
    getBalanceSnapshotDates: (...args: unknown[]) => getBalanceSnapshotDates(...args),
  },
}))

vi.mock('../api/references', () => ({
  referencesApi: {
    getObjects: (...args: unknown[]) => getObjects(...args),
    getProducts: (...args: unknown[]) => getProducts(...args),
    getProduct: (...args: unknown[]) => getProduct(...args),
  },
}))

vi.mock('antd', async () => {
  const actual = await vi.importActual<typeof import('antd')>('antd')
  return {
    ...actual,
    DatePicker: ({
      value,
      onChange,
      disabledDate,
      'aria-label': ariaLabel,
      placeholder,
    }: {
      value?: { format: (fmt: string) => string } | null
      onChange?: (value: ReturnType<typeof dayjs> | null) => void
      disabledDate?: (value: ReturnType<typeof dayjs>) => boolean
      'aria-label'?: string
      placeholder?: string
    }) => (
      <input
        aria-label={ariaLabel}
        placeholder={placeholder}
        value={value?.format('YYYY-MM-DD') ?? ''}
        data-snapshot-open={String(disabledDate ? !disabledDate(dayjs('2026-10-27')) : false)}
        data-other-open={String(disabledDate ? !disabledDate(dayjs('2026-01-01')) : false)}
        onChange={(event) =>
          onChange?.(event.target.value ? dayjs(event.target.value) : null)
        }
      />
    ),
  }
})

describe('BalanceHistoryPage', () => {
  beforeEach(() => {
    getBalanceHistory.mockReset()
    getBalanceSnapshotDates.mockReset()
    getObjects.mockReset()
    getProducts.mockReset()
    getProduct.mockReset()
    getObjects.mockResolvedValue({
      data: {
        status: 'success',
        data: [{ code: 2001, name: 'Склад Ростов', type: 'warehouse', is_active: true }],
      },
    })
    getProducts.mockResolvedValue({
      data: {
        status: 'success',
        data: [
          {
            code: 10001,
            name: 'Подшипник',
            category: 'A',
            plant_id: 1001,
            plant_name: 'Завод',
            weight_kg: 0.25,
            is_active: true,
          },
        ],
      },
    })
    getProduct.mockResolvedValue({
      data: {
        status: 'success',
        data: {
          code: 10001,
          name: 'Подшипник',
          category: 'A',
          plant_id: 1001,
          plant_name: 'Завод',
          weight_kg: 0.25,
          is_active: true,
        },
      },
    })
    getBalanceSnapshotDates.mockResolvedValue({
      data: { status: 'success', data: ['2026-10-27'] },
    })
    getBalanceHistory.mockResolvedValue({
      data: {
        status: 'success',
        data: [row],
        meta: { page: 1, limit: 50, total: 1 },
      },
    })
  })

  it('asks for a snapshot date and loads that day with extra filters', async () => {
    render(
      <MemoryRouter>
        <BalanceHistoryPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('История доступных остатков')).toBeTruthy()
    expect(screen.getByText('Выберите дату снимка')).toBeTruthy()
    await waitFor(() => {
      const picker = screen.getByLabelText('Дата снимка')
      expect(picker.getAttribute('data-snapshot-open')).toBe('true')
      expect(picker.getAttribute('data-other-open')).toBe('false')
    })
    expect(getBalanceHistory).not.toHaveBeenCalled()

    fireEvent.change(screen.getByLabelText('Дата снимка'), {
      target: { value: '2026-10-27' },
    })
    fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Склад' }))
    fireEvent.click(await screen.findByText('2001 — Склад Ростов', { selector: 'div' }))
    const productSelect = screen
      .getByTestId('product-filter')
      .querySelector('.ant-select-selector')
    fireEvent.mouseDown(productSelect as Element)
    fireEvent.click(await screen.findByText('10001 — Подшипник', { selector: 'span' }))
    fireEvent.click(screen.getByRole('button', { name: 'Применить фильтр' }))

    await waitFor(() => {
      expect(getBalanceHistory).toHaveBeenCalledWith({
        date_from: '2026-10-27',
        date_to: '2026-10-27',
        warehouse_code: 2001,
        product_code: 10001,
        page: 1,
        limit: 50,
      })
    })
    expect(screen.getByRole('cell', { name: '2001 — Склад Ростов' })).toBeTruthy()
    expect(screen.getByRole('cell', { name: '10001 — Подшипник' })).toBeTruthy()
    expect(screen.queryByText('Выберите дату снимка')).toBeNull()
  })
})