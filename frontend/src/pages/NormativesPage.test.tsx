import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import dayjs from 'dayjs'
import { NormativesPage } from './NormativesPage'
import type { NormativeOnDateItem } from '../api/types'

vi.mock('antd', async () => {
  const actual = await vi.importActual<typeof import('antd')>('antd')
  return {
    ...actual,
    DatePicker: ({
      value,
      onChange,
      'aria-label': ariaLabel,
      placeholder,
    }: {
      value?: { format: (fmt: string) => string }
      onChange?: (value: ReturnType<typeof dayjs>) => void
      'aria-label'?: string
      placeholder?: string
    }) => (
      <input
        aria-label={ariaLabel}
        placeholder={placeholder}
        value={value?.format('YYYY-MM-DD') ?? ''}
        onChange={(event) => onChange?.(dayjs(event.target.value))}
      />
    ),
  }
})

const getOnDate = vi.fn()
const getObjects = vi.fn()
const getDepartments = vi.fn()

vi.mock('../api/normatives', () => ({
  normativesApi: {
    getOnDate: (...args: unknown[]) => getOnDate(...args),
  },
}))

vi.mock('../api/references', () => ({
  referencesApi: {
    getObjects: (...args: unknown[]) => getObjects(...args),
    getDepartments: (...args: unknown[]) => getDepartments(...args),
  },
}))

const onDateData: NormativeOnDateItem[] = [
  {
    product_code: 10001,
    product_name: 'Подшипник 6204ZZ',
    warehouse_code: 2001,
    warehouse_name: 'Склад Ростов',
    total_quantity: 1000,
    unit: 'шт',
    category: 'A',
    details: [
      {
        client_name: "ООО 'Ромашка'",
        quantity: 1000,
        expiry_date: '2026-12-31',
        department_name: 'Коммерческий отдел',
      },
    ],
  },
  {
    product_code: 10002,
    product_name: 'Корпус чугунный',
    warehouse_code: 2002,
    warehouse_name: 'Склад Владивосток',
    total_quantity: 500,
    unit: 'шт',
    category: 'B',
    details: [
      {
        client_name: "ООО 'Ромашка'",
        quantity: 500,
        expiry_date: '2026-12-31',
      },
    ],
  },
]

const laterDateData: NormativeOnDateItem[] = [
  {
    product_code: 10005,
    product_name: 'Манжета 50x70x10',
    warehouse_code: 2001,
    warehouse_name: 'Склад Ростов',
    total_quantity: 200,
    unit: 'шт',
    category: 'A',
    details: [
      {
        client_name: 'ИП Петров',
        quantity: 200,
        expiry_date: '2027-06-30',
      },
    ],
  },
]

describe('NormativesPage', () => {
  beforeEach(() => {
    getOnDate.mockReset()
    getObjects.mockReset()
    getDepartments.mockReset()
    getOnDate.mockResolvedValue({
      data: { status: 'success', data: onDateData },
    })
    getObjects.mockResolvedValue({
      data: {
        status: 'success',
        data: [
          { code: 2001, name: 'Склад Ростов', city: 'Ростов', type: 'warehouse' },
          {
            code: 2002,
            name: 'Склад Владивосток',
            city: 'Владивосток',
            type: 'warehouse',
          },
        ],
      },
    })
    getDepartments.mockResolvedValue({
      data: {
        status: 'success',
        data: [{ id: 'dept-1', name: 'Коммерческий отдел', is_active: true }],
      },
    })
  })

  it('loads normatives for today and shows warehouse totals', async () => {
    render(
      <MemoryRouter>
        <NormativesPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Подшипник 6204ZZ')).toBeTruthy()
    })
    expect(getOnDate).toHaveBeenCalledWith({
      date: dayjs().format('YYYY-MM-DD'),
      warehouse_code: undefined,
      department_id: undefined,
      search: undefined,
    })
    expect(screen.getByText('Корпус чугунный')).toBeTruthy()
    expect(screen.getAllByText("ООО 'Ромашка'").length).toBeGreaterThan(0)
    expect(screen.getByText(/Склад Ростов: 1\s?000 шт/)).toBeTruthy()
    expect(screen.getByText(/Склад Владивосток: 500 шт/)).toBeTruthy()
    expect(screen.getByLabelText('Срез на дату')).toBeTruthy()
    expect(screen.getByRole('combobox', { name: 'Подразделение' })).toBeTruthy()
    expect(screen.getAllByText('Коммерческий отдел').length).toBeGreaterThan(0)
  })

  it('sends product search after debounce', async () => {
    render(
      <MemoryRouter>
        <NormativesPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Подшипник 6204ZZ')).toBeTruthy()
    })
    getOnDate.mockClear()

    fireEvent.change(screen.getByLabelText('Поиск по артикулу или названию'), {
      target: { value: 'подшипник' },
    })
    expect(getOnDate).not.toHaveBeenCalled()

    await waitFor(
      () => {
        expect(getOnDate).toHaveBeenCalledWith(
          expect.objectContaining({ search: 'подшипник' }),
        )
      },
      { timeout: 1000 },
    )
  })

  it('refetches when the slice date changes', async () => {
    getOnDate
      .mockResolvedValueOnce({ data: { status: 'success', data: onDateData } })
      .mockResolvedValue({ data: { status: 'success', data: laterDateData } })

    render(
      <MemoryRouter>
        <NormativesPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Подшипник 6204ZZ')).toBeTruthy()
    })

    fireEvent.change(screen.getByLabelText('Срез на дату'), {
      target: { value: '2026-12-31' },
    })

    await waitFor(() => {
      const dates = getOnDate.mock.calls.map(
        (call) => (call[0] as { date: string }).date,
      )
      expect(dates).toContain('2026-12-31')
    })
    await waitFor(() => {
      expect(screen.getByText('Манжета 50x70x10')).toBeTruthy()
    })
  })

  it('filters rows by client and category', async () => {
    render(
      <MemoryRouter>
        <NormativesPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Корпус чугунный')).toBeTruthy()
    })

    fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Категория' }))
    fireEvent.click(await screen.findByText('A', { selector: '.ant-select-item-option-content' }))
    await waitFor(() => {
      expect(screen.queryByText('Корпус чугунный')).toBeNull()
    })
    expect(screen.getByText('Подшипник 6204ZZ')).toBeTruthy()

    fireEvent.change(screen.getByLabelText('Клиент'), {
      target: { value: 'нет такого клиента' },
    })
    await waitFor(() => {
      expect(screen.queryByText('Подшипник 6204ZZ')).toBeNull()
    })
  })
})
