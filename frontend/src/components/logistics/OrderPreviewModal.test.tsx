import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { OrderPreviewModal } from './OrderPreviewModal'
import type { GeneratedOrder } from '../../api/types'

const routes: GeneratedOrder[] = [
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
      {
        product_code: 10002,
        product_name: 'Корпус чугунный',
        deficit: 200,
        unit: 'шт',
        weight_kg: 2.5,
      },
    ],
  },
  {
    plant_code: 1002,
    plant_name: 'Завод Екатеринбургский',
    warehouse_code: 2003,
    warehouse_name: 'Склад Казань',
    estimated_delivery_days: 5,
    items: [
      {
        product_code: 10003,
        product_name: 'Вал приводной 500мм',
        deficit: 80,
        unit: 'шт',
        weight_kg: 1,
      },
    ],
  },
]

describe('OrderPreviewModal', () => {
  it('selects all routes by default and keeps positions collapsed', () => {
    render(
      <OrderPreviewModal
        open
        routes={routes}
        onClose={() => undefined}
        onConfirm={() => undefined}
        onExportB2B={() => undefined}
      />,
    )
    expect(screen.getByText('📦 Предпросмотр заказов')).toBeTruthy()
    expect(screen.getByRole('checkbox', { name: 'Выбрать все маршруты' })).toHaveProperty(
      'checked',
      true,
    )
    expect(
      screen.getByRole('checkbox', {
        name: /Завод Московский → Склад Ростов/,
      }),
    ).toHaveProperty('checked', true)
    expect(screen.getByText(/2 позиции, 600 кг/)).toBeTruthy()
    expect(screen.getByText(/1 позиция, 80 кг/)).toBeTruthy()
    expect(screen.queryByText('Подшипник 6204ZZ')).toBeNull()
    expect(screen.queryByText('Корпус чугунный')).toBeNull()
    expect(screen.queryByText('Вал приводной 500мм')).toBeNull()
    expect(screen.getByRole('button', { name: /Выгрузить для B2B \(2 маршрутов\)/ })).toHaveProperty(
      'disabled',
      false,
    )
  })

  it('expands positions under the matching route', () => {
    render(
      <OrderPreviewModal
        open
        routes={routes}
        onClose={() => undefined}
        onConfirm={() => undefined}
        onExportB2B={() => undefined}
      />,
    )
    fireEvent.click(
      screen.getByRole('button', {
        name: 'Показать позиции: Завод Московский → Склад Ростов',
      }),
    )
    expect(screen.getByText('Подшипник 6204ZZ')).toBeTruthy()
    expect(screen.getByText('Корпус чугунный')).toBeTruthy()
    expect(screen.queryByText('Вал приводной 500мм')).toBeNull()

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Показать позиции: Завод Екатеринбургский → Склад Казань',
      }),
    )
    expect(screen.getByText('Вал приводной 500мм')).toBeTruthy()
    expect(screen.getByText('Подшипник 6204ZZ')).toBeTruthy()

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Скрыть позиции: Завод Московский → Склад Ростов',
      }),
    )
    expect(screen.queryByText('Подшипник 6204ZZ')).toBeNull()
    expect(screen.queryByText('Корпус чугунный')).toBeNull()
    expect(screen.getByText('Вал приводной 500мм')).toBeTruthy()
  })

  it('disables B2B export when no routes are selected', () => {
    render(
      <OrderPreviewModal
        open
        routes={routes}
        onClose={() => undefined}
        onConfirm={() => undefined}
        onExportB2B={() => undefined}
      />,
    )
    fireEvent.click(screen.getByRole('checkbox', { name: 'Выбрать все маршруты' }))
    expect(
      screen.getByRole('button', { name: /Выгрузить для B2B \(0 маршрутов\)/ }),
    ).toHaveProperty('disabled', true)
  })

  it('exports only checked routes and confirms all routes separately', () => {
    const onExportB2B = vi.fn()
    const onConfirm = vi.fn()
    render(
      <OrderPreviewModal
        open
        routes={routes}
        onClose={() => undefined}
        onConfirm={onConfirm}
        onExportB2B={onExportB2B}
      />,
    )
    fireEvent.click(
      screen.getByRole('checkbox', {
        name: /Завод Екатеринбургский → Склад Казань/,
      }),
    )
    fireEvent.click(screen.getByRole('button', { name: /Выгрузить для B2B/ }))
    expect(onExportB2B).toHaveBeenCalledTimes(1)
    expect(onExportB2B.mock.calls[0][0]).toEqual([routes[0]])

    fireEvent.click(screen.getByRole('button', { name: 'Подтвердить' }))
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })
})
