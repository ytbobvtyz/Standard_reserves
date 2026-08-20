import api from './client'
import type {
  ApiSuccess,
  ExecuteOneTimeData,
  ExecuteOneTimePayload,
  GenerateOrdersBulkPayload,
  GenerateOrdersData,
  GenerateOrdersPayload,
  LogisticsDashboardData,
  LogisticsDashboardParams,
  OneTimeInitiator,
  OneTimeListItem,
  OneTimeListParams,
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

  getOneTimeList: (params?: OneTimeListParams) =>
    api.get<ApiSuccess<OneTimeListItem[]>>('/logistics/one-time/list', { params }),

  executeOneTime: (id: string, data: ExecuteOneTimePayload) =>
    api.post<ApiSuccess<ExecuteOneTimeData>>(`/logistics/one-time/${id}/execute`, data),

  getInitiators: () =>
    api.get<ApiSuccess<OneTimeInitiator[]>>('/logistics/one-time/initiators'),

  getClients: () => api.get<ApiSuccess<string[]>>('/logistics/one-time/clients'),

  exportOneTime: (id: string) =>
    api.get<Blob>(`/logistics/one-time/${id}/export`, { responseType: 'blob' }),
}
