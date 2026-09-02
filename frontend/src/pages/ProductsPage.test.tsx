import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ProductsPage } from './ProductsPage'
import { useAuthStore } from '../stores/auth'
import type { ProductListItem } from '../api/types'

const product: ProductListItem = {
  code: 10001,
  name: 'Подшипник 6204ZZ',
  category: 'A',
  plant_id: 1001,
  plant_name: 'Завод Московский',
  weight_kg: 0.25,
  monthly_consumption: 1000,
  is_active: true,
  gtin: '4601234567890',
  mark_control: false,
  last_modified_at: '2026-08-20T12:00:00Z',
}

const getProducts = vi.fn()
const getProductForEdit = vi.fn()
const updateProduct = vi.fn()
const deleteProduct = vi.fn()
const downloadProductsTemplate = vi.fn()
const exportProducts = vi.fn()
const uploadProducts = vi.fn()
const getObjects = vi.fn()
const getProduct = vi.fn()

vi.mock('../api/references', () => ({
  referencesApi: {
    getProducts: (...args: unknown[]) => getProducts(...args),
    getProductForEdit: (...args: unknown[]) => getProductForEdit(...args),
    updateProduct: (...args: unknown[]) => updateProduct(...args),
    deleteProduct: (...args: unknown[]) => deleteProduct(...args),
    downloadProductsTemplate: (...args: unknown[]) => downloadProductsTemplate(...args),
    exportProducts: (...args: unknown[]) => exportProducts(...args),
    uploadProducts: (...args: unknown[]) => uploadProducts(...args),
    getObjects: (...args: unknown[]) => getObjects(...args),
    getProduct: (...args: unknown[]) => getProduct(...args),
  },
}))

vi.mock('../utils/download', () => ({
  downloadBlob: vi.fn(),
  filenameFromContentDisposition: (header?: string) => {
    if (!header) {
      return null
    }
    const match = /filename="?([^";]+)"?/i.exec(header)
    return match?.[1] ?? null
  },
}))

function setRole(role: 'pp' | 'commercial') {
  useAuthStore.setState({
    user: {
      id: '22222222-2222-2222-2222-222222222222',
      username: role,
      full_name: role === 'pp' ? 'Петров Петр' : 'Иванов Иван',
      role,
    },
    token: 'token',
    isAuthenticated: true,
    isLoading: false,
  })
}

describe('ProductsPage', () => {
  beforeEach(() => {
    getProducts.mockReset()
    getProductForEdit.mockReset()
    updateProduct.mockReset()
    deleteProduct.mockReset()
    downloadProductsTemplate.mockReset()
    exportProducts.mockReset()
    uploadProducts.mockReset()
    getObjects.mockReset()
    getProduct.mockReset()
    URL.createObjectURL = vi.fn(() => 'blob:url')
    URL.revokeObjectURL = vi.fn()

    getProducts.mockResolvedValue({
      data: {
        status: 'success',
        data: [product],
        meta: { page: 1, limit: 10, total: 1 },
      },
    })
    getObjects.mockResolvedValue({
      data: {
        status: 'success',
        data: [
          {
            code: 1001,
            name: 'Завод Московский',
            city: 'Москва',
            type: 'plant',
            is_active: true,
          },
        ],
      },
    })
    getProductForEdit.mockResolvedValue({
      data: {
        status: 'success',
        data: {
          ...product,
          description: null,
          second_plant_id: null,
          third_plant_id: null,
          parent_code: null,
          children_code: null,
          last_modified_by: {
            id: '22222222-2222-2222-2222-222222222222',
            full_name: 'Петров Петр',
          },
        },
      },
    })
    getProduct.mockResolvedValue({
      data: { status: 'success', data: product },
    })
    updateProduct.mockResolvedValue({
      data: { status: 'success', data: product },
    })
    deleteProduct.mockResolvedValue({
      data: { status: 'success', message: 'Продукт удален' },
    })
    downloadProductsTemplate.mockResolvedValue({
      data: new Blob(['xlsx']),
    })
    exportProducts.mockResolvedValue({
      data: new Blob(['xlsx']),
      headers: {
        'content-disposition': 'attachment; filename="products_export_2026-08-31.xlsx"',
      },
    })
    uploadProducts.mockResolvedValue({
      data: {
        status: 'success',
        data: {
          created: 1,
          updated: 0,
          errors: 1,
          message: 'Загружено 1, ошибок 1',
          error_details: [{ row: 3, message: 'GTIN должен содержать 13 цифр' }],
        },
      },
    })
    setRole('pp')
  })

  it('shows management buttons and extra columns for pp', async () => {
    render(
      <MemoryRouter>
        <ProductsPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Подшипник 6204ZZ')).toBeTruthy()
    })
    expect(screen.getByRole('button', { name: /Выгрузить в Excel/ })).toBeTruthy()
    expect(screen.getByPlaceholderText('Поиск по GTIN')).toBeTruthy()
    expect(screen.getByRole('button', { name: /Выгрузить шаблон/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: /Загрузить из Excel/ })).toBeTruthy()
    expect(screen.getByText('GTIN')).toBeTruthy()
    expect(screen.getByText('Честный знак')).toBeTruthy()
    expect(screen.getByText('Дата изменения')).toBeTruthy()
    expect(screen.getByText('4601234567890')).toBeTruthy()
  })

  it('hides management buttons for commercial', async () => {
    setRole('commercial')
    render(
      <MemoryRouter>
        <ProductsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Подшипник 6204ZZ')).toBeTruthy()
    })
    expect(screen.queryByRole('button', { name: /Выгрузить шаблон/ })).toBeNull()
    expect(screen.queryByRole('button', { name: /Загрузить из Excel/ })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Редактировать' })).toBeNull()
    expect(screen.getByRole('button', { name: /Выгрузить в Excel/ })).toBeTruthy()
    expect(screen.getByPlaceholderText('Поиск по GTIN')).toBeTruthy()
  })

  it('searches by GTIN and exports filtered products', async () => {
    render(
      <MemoryRouter>
        <ProductsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Подшипник 6204ZZ')).toBeTruthy()
    })
    fireEvent.change(screen.getByPlaceholderText('Поиск по GTIN'), {
      target: { value: '460123' },
    })
    fireEvent.click(document.querySelectorAll('.ant-input-search-button')[1] as HTMLElement)
    await waitFor(() => {
      expect(getProducts).toHaveBeenCalledWith(
        expect.objectContaining({ gtin: '460123' }),
      )
    })
    fireEvent.click(screen.getByRole('button', { name: /Выгрузить в Excel/ }))
    await waitFor(() => {
      expect(exportProducts).toHaveBeenCalledWith(
        expect.objectContaining({ gtin: '460123' }),
      )
    })
  })

  it('opens upload modal and shows report', async () => {
    render(
      <MemoryRouter>
        <ProductsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Подшипник 6204ZZ')).toBeTruthy()
    })
    fireEvent.click(screen.getByRole('button', { name: /Загрузить из Excel/ }))
    expect(screen.getByText('Загрузить продукты')).toBeTruthy()
    expect(screen.getByText(/Перетащите Excel-файл/)).toBeTruthy()

    const file = new File(['data'], 'products.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(input, { target: { files: [file] } })

    await waitFor(() => {
      expect(uploadProducts).toHaveBeenCalled()
    })
    await waitFor(() => {
      expect(screen.getByText('Загружено 1, ошибок 1')).toBeTruthy()
    })
    expect(screen.getByText(/Строка 3/)).toBeTruthy()
  }, 15000)

  it('opens edit modal and deletes with confirmation', async () => {
    render(
      <MemoryRouter>
        <ProductsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Подшипник 6204ZZ')).toBeTruthy()
    })
    fireEvent.click(screen.getByRole('button', { name: 'Редактировать' }))
    await waitFor(() => {
      expect(getProductForEdit).toHaveBeenCalledWith(10001)
    })
    expect(screen.getByText('Редактировать продукт')).toBeTruthy()
    expect(screen.getByDisplayValue('Подшипник 6204ZZ')).toBeTruthy()
    expect(screen.getByText('Удалить')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Удалить' }))
    await waitFor(() => {
      expect(screen.getByText('Удалить продукт?')).toBeTruthy()
    })
    const confirmButtons = screen.getAllByRole('button', { name: 'Удалить' })
    fireEvent.click(confirmButtons[confirmButtons.length - 1])
    await waitFor(() => {
      expect(deleteProduct).toHaveBeenCalledWith(10001)
    })
  }, 15000)
})
