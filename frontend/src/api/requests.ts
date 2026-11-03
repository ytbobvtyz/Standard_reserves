import api from './client'
import type {
  ApiSuccess,
  OptimalCalculateData,
  OptimalCalculateItem,
  OverlappingRequestRef,
  RequestCreatePayload,
  RequestDetail,
  RequestItemHistoryEntry,
  RequestListItem,
  RequestListParams,
  RequestStatusData,
} from './types'

export const requestsApi = {
  list: (params?: RequestListParams) =>
    api.get<ApiSuccess<RequestListItem[]>>('/requests', { params }),

  get: (id: string) => api.get<ApiSuccess<RequestDetail>>(`/requests/${id}`),

  create: (payload: RequestCreatePayload) =>
    api.post<ApiSuccess<RequestDetail>>('/requests', payload),

  calculateOptimal: (payload: {
    client_id: string
    items: OptimalCalculateItem[]
  }) =>
    api.post<ApiSuccess<OptimalCalculateData>>(
      '/requests/calculate-optimal',
      payload,
    ),

  update: (id: string, payload: Partial<RequestCreatePayload>) =>
    api.put<ApiSuccess<RequestStatusData>>(`/requests/${id}`, payload),

  remove: (id: string) =>
    api.delete<{ status: string; message: string }>(`/requests/${id}`),

  submit: (id: string, autoCompletePrevious = false) =>
    api.post<ApiSuccess<RequestStatusData>>(`/requests/${id}/submit`, {
      auto_complete_previous: autoCompletePrevious,
    }),

  overlapping: (payload: {
    client_id: string
    items: OptimalCalculateItem[]
    exclude_request_id?: string
  }) =>
    api.post<ApiSuccess<{ requests: OverlappingRequestRef[] }>>(
      '/requests/overlapping-normatives',
      payload,
    ),

  getHistory: (id: string) =>
    api.get<ApiSuccess<RequestItemHistoryEntry[]>>(`/requests/${id}/history`),

  exportExcel: (requestIds: string[]) =>
    api.post<Blob>(
      '/requests/export',
      { request_ids: requestIds },
      { responseType: 'blob' },
    ),

  updateExpiry: (id: string, expiry_date: string) =>
    api.patch<
      ApiSuccess<{
        id: string
        status: RequestStatusData['status']
        expiry_date: string | null
        updated_at: string
      }>
    >(`/requests/${id}/expiry-date`, { expiry_date }),
}
