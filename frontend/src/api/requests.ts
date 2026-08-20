import api from './client'
import type {
  ApiSuccess,
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

  update: (id: string, payload: Partial<RequestCreatePayload>) =>
    api.put<ApiSuccess<RequestStatusData>>(`/requests/${id}`, payload),

  remove: (id: string) =>
    api.delete<{ status: string; message: string }>(`/requests/${id}`),

  submit: (id: string) =>
    api.post<ApiSuccess<RequestStatusData>>(`/requests/${id}/submit`),

  getHistory: (id: string) =>
    api.get<ApiSuccess<RequestItemHistoryEntry[]>>(`/requests/${id}/history`),
}
