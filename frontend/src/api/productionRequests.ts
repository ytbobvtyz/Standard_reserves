import api from './client'
import type {
  ApiSuccess,
  ProductionRequestDatesPayload,
  ProductionRequestDetail,
  ProductionRequestListItem,
  ProductionRequestPreview,
  ProductionRequestUploadResult,
} from './types'

export const productionRequestsApi = {
  list: (params?: { page?: number; limit?: number }) =>
    api.get<ApiSuccess<ProductionRequestListItem[]>>('/production-requests', {
      params,
    }),

  preview: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post<ApiSuccess<ProductionRequestPreview>>(
      '/production-requests/preview',
      form,
    )
  },

  upload: (
    file: File,
    payload: ProductionRequestDatesPayload & {
      inactive_policy?: 'active_only' | 'include_inactive'
    },
  ) => {
    const form = new FormData()
    form.append('file', file)
    form.append('valid_from', payload.valid_from)
    form.append('valid_to', payload.valid_to)
    form.append('inactive_policy', payload.inactive_policy ?? 'active_only')
    return api.post<ApiSuccess<ProductionRequestUploadResult>>(
      '/production-requests/upload',
      form,
    )
  },

  updateDates: (id: string, payload: ProductionRequestDatesPayload) =>
    api.patch<ApiSuccess<ProductionRequestDetail>>(
      `/production-requests/${id}/dates`,
      payload,
    ),

  remove: (id: string) =>
    api.delete<{ status: 'success'; message: string }>(
      `/production-requests/${id}`,
    ),

  downloadTemplate: () =>
    api.get<Blob>('/production-requests/template', { responseType: 'blob' }),
}
