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
})
