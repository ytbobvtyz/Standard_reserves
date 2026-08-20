import api from './client'
import type {
  ApiSuccess,
  GenerateOrdersBulkPayload,
  GenerateOrdersData,
  GenerateOrdersPayload,
  LogisticsDashboardData,
  LogisticsDashboardParams,
} from './types'

export const logisticsApi = {
  getDashboard: (params?: LogisticsDashboardParams) =>
    api.get<LogisticsDashboardData>('/logistics/normative/dashboard', { params }),

  generateOrders: (warehouseCode: number, data?: GenerateOrdersPayload) =>
    api.post<ApiSuccess<GenerateOrdersData>>(
      `/logistics/normative/${warehouseCode}/generate-orders`,
      data ?? {},
    ),

  generateOrdersBulk: (data: GenerateOrdersBulkPayload) =>
    api.post<ApiSuccess<GenerateOrdersData>>(
      '/logistics/normative/generate-orders',
      data,
    ),

  exportOrders: (params?: LogisticsDashboardParams & { product_codes?: string }) =>
    api.get<Blob>('/logistics/normative/export', {
      params,
      responseType: 'blob',
    }),
}
