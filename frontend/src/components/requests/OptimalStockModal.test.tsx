import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { OptimalCalculateData } from '../../api/types'
import { OptimalStockModal } from './OptimalStockModal'

const result: OptimalCalculateData = {
  client_name: 'ООО Ромашка',
  items: [
    {
      product_code: 10001,
      warehouse_code: 2001,
      product_name: 'Подшипник 6204ZZ',
      warehouse_name: 'Склад Ростов',
      category: 'A',
      weight_kg: 0.25,
      pallet_qty: 48,
      calculated_quantity: 90.5,
      unit: 'кг',
      months_used: 5,
    },
  ],
  skipped_items: [
    {
      product_code: 10002,
      warehouse_code: 2001,
      product_name: 'Корпус чугунный',
      warehouse_name: 'Склад Ростов',
      reason: 'Реализация меньше 1 паллеты',
    },
  ],
  existing_normatives: [
    {
      id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
      request_id: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
      created_at: '2026-10-01',
      client_name: 'ООО Ромашка',
      quantity: 1000,
      unit: 'шт',
      expiry_date: '2026-12-31',
      product_code: 10001,
      product_name: 'Подшипник 6204ZZ',
    },
  ],
}

describe('OptimalStockModal', () => {
  it('shows calculated and skipped rows and applies the checked flag', () => {
    const onApply = vi.fn()
    render(
      <MemoryRouter>
        <OptimalStockModal
          open
          loading={false}
          result={result}
          overwriteLabels={['10001 Подшипник 6204ZZ — Склад Ростов']}
          onCancel={() => undefined}
          onApply={onApply}
        />
      </MemoryRouter>,
    )

    expect(screen.getByText(/ООО Ромашка/)).toBeTruthy()
    expect(
      screen.getByText('Количество в уже добавленных строках будет перезаписано'),
    ).toBeTruthy()
    expect(screen.getByText(/10001 Подшипник 6204ZZ/)).toBeTruthy()
    expect(screen.getAllByText('Подшипник 6204ZZ').length).toBeGreaterThan(0)
    expect(screen.getByText('90,5')).toBeTruthy()
    expect(screen.getByText('⚠️ Реализация меньше 1 паллеты')).toBeTruthy()
    const link = screen.getByRole('link', { name: 'открыть' })
    expect(link.getAttribute('href')).toBe(
      '/requests/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
    )
    expect(link.getAttribute('target')).toBe('_blank')
    expect(screen.queryByRole('checkbox')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: /Применить/ }))
    expect(onApply).toHaveBeenCalledOnce()
  })
})
