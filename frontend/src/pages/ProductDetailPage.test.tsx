import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ProductDetailPage } from './ProductDetailPage'

const getProduct = vi.fn()
const getRelated = vi.fn()

vi.mock('../api/references', () => ({
  referencesApi: {
    getProduct: (...args: unknown[]) => getProduct(...args),
    getRelated: (...args: unknown[]) => getRelated(...args),
  },
}))

describe('ProductDetailPage', () => {
  beforeEach(() => {
    getProduct.mockReset()
    getRelated.mockReset()
    getProduct.mockResolvedValue({
      data: {
        status: 'success',
        data: {
          code: 10001,
          name: 'Подшипник 6204ZZ',
          category: 'A',
          plant_id: 1001,
          plant_name: 'Завод Московский',
          weight_kg: 0.25,
          monthly_consumption: 1000,
          is_active: true,
        },
      },
    })
    getRelated.mockResolvedValue({
      data: {
        status: 'success',
        data: {
          product_code: 10001,
          product_name: 'Подшипник 6204ZZ',
          related_products: [
            {
              code: 10004,
              name: 'Подшипник 6204ZZ-NEW',
              relation: 'child',
              is_active: true,
            },
          ],
        },
      },
    })
  })

  it('shows related product chain', async () => {
    render(
      <MemoryRouter initialEntries={['/references/products/10001']}>
        <Routes>
          <Route path="/references/products/:code" element={<ProductDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Подшипник 6204ZZ-NEW')).toBeTruthy()
    })
    expect(screen.getByText('Родственные артикулы')).toBeTruthy()
    expect(screen.getByText('Дочерний')).toBeTruthy()
    expect(getRelated).toHaveBeenCalledWith(10001)
  })
})
