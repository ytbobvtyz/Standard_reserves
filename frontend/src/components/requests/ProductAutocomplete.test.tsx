import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ProductAutocomplete } from './ProductAutocomplete'

const getProducts = vi.fn()
const getProduct = vi.fn()

vi.mock('../../api/references', () => ({
  referencesApi: {
    getProducts: (...args: unknown[]) => getProducts(...args),
    getProduct: (...args: unknown[]) => getProduct(...args),
  },
}))

describe('ProductAutocomplete', () => {
  it('requests analogs and shows analog mark', async () => {
    getProducts.mockResolvedValue({
      data: {
        status: 'success',
        data: [
          {
            code: 10001,
            name: 'Подшипник 6204ZZ',
            category: 'A',
            is_analog: false,
          },
          {
            code: 10101,
            name: 'Подшипник 6204ZZ (новая этикетка)',
            category: 'A',
            is_analog: true,
          },
        ],
      },
    })

    render(<ProductAutocomplete includeAnalogs />)

    await waitFor(() => {
      expect(getProducts).toHaveBeenCalledWith(
        expect.objectContaining({ include_analogs: true, is_active: true }),
      )
    })
    fireEvent.mouseDown(screen.getByRole('combobox'))
    expect(await screen.findByText('Аналог')).toBeTruthy()
  })

  it('shows an inactive exact match but does not allow selecting it', async () => {
    const onChange = vi.fn()
    getProducts.mockResolvedValue({
      data: {
        status: 'success',
        data: [
          {
            code: 19465,
            name: 'Выведенный материал',
            category: 'A',
            is_active: false,
            is_analog: false,
          },
          {
            code: 3705297,
            name: 'Действующий материал',
            category: 'A',
            is_active: true,
            is_analog: true,
          },
        ],
      },
    })

    render(<ProductAutocomplete includeAnalogs onChange={onChange} />)

    fireEvent.mouseDown(screen.getByRole('combobox'))
    const inactiveMark = await screen.findByText('Не активен')
    const inactiveOption = inactiveMark.closest('.ant-select-item-option')
    expect(inactiveOption?.classList.contains('ant-select-item-option-disabled')).toBe(true)

    fireEvent.click(inactiveMark)
    expect(onChange).not.toHaveBeenCalled()
    expect(screen.getByText('Аналог')).toBeTruthy()
  })
})
