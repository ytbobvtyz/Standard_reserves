import api from './client'
import type {
  ApiSuccess,
  B2BExportRequest,
  BalanceHistoryItem,
  BalanceHistoryParams,
  BalancePreviewResult,
  BalanceSyncInfo,
  BalanceUploadResult,
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

  exportB2B: (data: B2BExportRequest) =>
    api.post<Blob>('/logistics/normative/export-b2b', data, {
      responseType: 'blob',
    }),

  previewBalances: (availableFile: File, movingFile: File) => {
    const form = new FormData()
    form.append('available_file', availableFile)
    form.append('moving_file', movingFile)
    return api.post<ApiSuccess<BalancePreviewResult>>(
      '/logistics/normative/preview',
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
  },

  uploadBalances: (availableFile: File, movingFile: File) => {
    const form = new FormData()
    form.append('available_file', availableFile)
    form.append('moving_file', movingFile)
    return api.post<ApiSuccess<BalanceUploadResult>>(
      '/logistics/normative/upload',
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
  },

  getSyncInfo: () =>
    api.get<ApiSuccess<BalanceSyncInfo>>('/logistics/normative/sync-info'),

  getBalanceHistory: (params?: BalanceHistoryParams) =>
    api.get<ApiSuccess<BalanceHistoryItem[]>>('/logistics/normative/history', { params }),

  getBalanceSnapshotDates: () =>
    api.get<ApiSuccess<string[]>>('/logistics/normative/history/dates'),

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
