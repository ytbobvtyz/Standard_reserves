import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ActualShipmentListItem, ActualShipmentUploadResult } from '../api/types'
import { ActualShipmentsPage } from './ActualShipmentsPage'
import { useAuthStore } from '../stores/auth'

const shipment: ActualShipmentListItem = {
  id: 'ship-1',
  client_id: 'client-1',
  client_code: 100,
  client_name: 'ООО Ромашка',
  product_code: 10001,
  product_name: 'Подшипник',
  quantity: 12.5,
  unit: 'кг',
  shipment_date: '2026-10-01',
  loading_point: '2R05',
  invoice_number: 'НК-1',
  route: 'Север',
}

const preview: ActualShipmentUploadResult = {
  saved: false,
  total_rows: 2,
  valid_rows: 1,
  inserted: 0,
  skipped_rows: 0,
  errors: 1,
  message: 'К загрузке 1 строк, ошибок 1. Данные не сохранены.',
  preview: [
    {
      row: 2,
      client_id: 'client-1',
      client_code: 100,
      client_name: 'ООО Ромашка',
      product_code: 10001,
      product_name: 'Подшипник',
      quantity: 12.5,
      unit: 'кг',
      shipment_date: '2026-10-01',
      loading_point: '2R05',
      invoice_number: 'НК-1',
      route: 'Север',
    },
  ],
  error_details: [{ row: 3, message: 'Вес нетто должен быть больше 0' }],
  missing_clients: [{ client_code: 999, client_name: 'Чужой клиент', rows: 1 }],
  missing_products: [],
}

const listShipments = vi.fn()
const uploadShipments = vi.fn()
const downloadTemplate = vi.fn()
const listClients = vi.fn()
const getClient = vi.fn()
const getProducts = vi.fn()
const getProduct = vi.fn()
const getObjects = vi.fn()

vi.mock('../api/actualShipments', () => ({
  actualShipmentsApi: {
    list: (...args: unknown[]) => listShipments(...args),
    upload: (...args: unknown[]) => uploadShipments(...args),
    downloadTemplate: (...args: unknown[]) => downloadTemplate(...args),
  },
}))

vi.mock('../api/clients', () => ({
  clientsApi: {
    list: (...args: unknown[]) => listClients(...args),
    get: (...args: unknown[]) => getClient(...args),
  },
}))

vi.mock('../api/references', () => ({
  referencesApi: {
    getProducts: (...args: unknown[]) => getProducts(...args),
    getProduct: (...args: unknown[]) => getProduct(...args),
    getObjects: (...args: unknown[]) => getObjects(...args),
  },
}))

function setRole(role: 'logistics' | 'commercial' | 'pp' | 'guest') {
  useAuthStore.setState({
    user: {
      id: 'user-1',
      username: role,
      full_name: 'Тестовый пользователь',
      role,
    },
    token: 'token',
    isAuthenticated: true,
    isLoading: false,
  })
}

describe('ActualShipmentsPage', () => {
  beforeEach(() => {
    listShipments.mockReset()
    uploadShipments.mockReset()
    downloadTemplate.mockReset()
    listClients.mockReset()
    getClient.mockReset()
    getProducts.mockReset()
    getProduct.mockReset()
    getObjects.mockReset()
    URL.createObjectURL = vi.fn(() => 'blob:url')
    URL.revokeObjectURL = vi.fn()
    listShipments.mockResolvedValue({
      data: {
        status: 'success',
        data: [shipment],
        meta: { page: 1, limit: 20, total: 1 },
      },
    })
    const clientItem = {
      id: 'client-1',
      client_code: 100,
      inn: '7700000000',
      name: 'ООО Ромашка',
      is_active: true,
      is_system: false,
    }
    listClients.mockResolvedValue({
      data: {
        status: 'success',
        data: [clientItem],
        meta: { page: 1, limit: 20, total: 1 },
      },
    })
    getClient.mockResolvedValue({
      data: { status: 'success', data: clientItem },
    })
    const productItem = {
      code: 10001,
      name: 'Подшипник',
      category: 'A',
      plant_id: 1001,
      plant_name: 'Завод',
      weight_kg: 0.25,
      monthly_consumption: null,
      is_active: true,
    }
    getProducts.mockResolvedValue({
      data: {
        status: 'success',
        data: [productItem],
      },
    })
    getProduct.mockResolvedValue({
      data: { status: 'success', data: productItem },
    })
    getObjects.mockResolvedValue({
      data: {
        status: 'success',
        data: [
          {
            code: 2001,
            name: 'Склад Ростов',
            city: 'Ростов-на-Дону',
            type: 'warehouse',
            loading_point: '2R05',
            is_active: true,
          },
          {
            code: 2002,
            name: 'Склад без пункта',
            city: 'Владивосток',
            type: 'warehouse',
            loading_point: null,
            is_active: true,
          },
        ],
      },
    })
    uploadShipments.mockImplementation(async (_file: File, confirm: boolean) => ({
      data: {
        status: 'success',
        data: confirm
          ? { ...preview, saved: true, inserted: 1, message: 'Сохранено 1, ошибок 1' }
          : preview,
      },
    }))
    downloadTemplate.mockResolvedValue({ data: new Blob(['xlsx']) })
    setRole('logistics')
  })

  it('shows shipments to every role and hides upload buttons from guests', async () => {
    setRole('guest')
    render(
      <MemoryRouter>
        <ActualShipmentsPage />
      </MemoryRouter>,
    )
    expect(screen.getByText('Продажи')).toBeTruthy()
    await waitFor(() => {
      expect(screen.getByText('100 — ООО Ромашка')).toBeTruthy()
    })
    expect(screen.getByText('10001 — Подшипник')).toBeTruthy()
    expect(screen.getByText('01.10.2026')).toBeTruthy()
    expect(screen.getByText('2R05')).toBeTruthy()
    expect(screen.getByText('НК-1')).toBeTruthy()
    expect(screen.getByText('Север')).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Загрузить из Excel/ })).toBeNull()
    expect(screen.queryByRole('button', { name: /Выгрузить шаблон/ })).toBeNull()
  })

  it('filters by client and article', async () => {
    render(
      <MemoryRouter>
        <ActualShipmentsPage />
      </MemoryRouter>,
    )
    await screen.findByText('100 — ООО Ромашка')

    const clientSelect = screen
      .getByTestId('client-filter')
      .querySelector('.ant-select-selector')
    fireEvent.mouseDown(clientSelect as Element)
    fireEvent.click(await screen.findByText('100 — ООО Ромашка', { selector: 'span' }))
    const productSelect = screen
      .getByTestId('product-filter')
      .querySelector('.ant-select-selector')
    fireEvent.mouseDown(productSelect as Element)
    fireEvent.click(await screen.findByText('10001 — Подшипник', { selector: 'span' }))
    fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Склад' }))
    expect(screen.queryByText('2002 — Склад без пункта')).toBeNull()
    fireEvent.click(await screen.findByText('2001 — Склад Ростов', { selector: 'div' }))
    fireEvent.click(screen.getByRole('button', { name: 'Применить фильтр' }))

    await waitFor(() => {
      expect(listShipments).toHaveBeenCalledWith(
        expect.objectContaining({
          client_id: 'client-1',
          product_code: 10001,
          warehouse_code: 2001,
          page: 1,
          limit: 20,
        }),
      )
    })
  })

  it('previews an excel file and saves only after confirmation', async () => {
    setRole('pp')
    render(
      <MemoryRouter>
        <ActualShipmentsPage />
      </MemoryRouter>,
    )
    await screen.findByText('100 — ООО Ромашка')
    expect(screen.getByRole('button', { name: /Выгрузить шаблон/ })).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /Загрузить из Excel/ }))
    const file = new File(['data'], 'shipments.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(input, { target: { files: [file] } })

    await waitFor(() => {
      expect(uploadShipments).toHaveBeenCalledWith(file, false)
    })
    expect(await screen.findByText(/К загрузке 1 строк/)).toBeTruthy()
    expect(screen.getByText(/999 — Чужой клиент: 1/)).toBeTruthy()
    expect(screen.getByText(/Строка 3: Вес нетто должен быть больше 0/)).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Отмена' }))
    expect(uploadShipments).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByRole('button', { name: /Загрузить из Excel/ }))
    const inputAgain = document.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(inputAgain, { target: { files: [file] } })
    await screen.findByText(/К загрузке 1 строк/)
    fireEvent.click(screen.getByRole('button', { name: 'Сохранить' }))

    await waitFor(() => {
      expect(uploadShipments).toHaveBeenCalledWith(file, true)
    })
    await waitFor(() => {
      expect(screen.getByText('Сохранено 1, ошибок 1')).toBeTruthy()
    })
  })
})
