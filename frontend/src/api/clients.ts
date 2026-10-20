import api from './client'
import type {
  ApiSuccess,
  ClientCreatePayload,
  ClientListItem,
  ClientListParams,
  ClientUpdatePayload,
  ClientUploadPreview,
  ClientUploadResult,
} from './types'

export const clientsApi = {
  list: (params?: ClientListParams) =>
    api.get<ApiSuccess<ClientListItem[]>>('/references/clients', { params }),

  get: (id: string) => api.get<ApiSuccess<ClientListItem>>(`/references/clients/${id}`),

  create: (payload: ClientCreatePayload) =>
    api.post<ApiSuccess<ClientListItem>>('/references/clients', payload),

  update: (id: string, payload: ClientUpdatePayload) =>
    api.put<ApiSuccess<ClientListItem>>(`/references/clients/${id}`, payload),

  remove: (id: string) =>
    api.delete<{ status: 'success'; message: string }>(`/references/clients/${id}`),

  downloadTemplate: () =>
    api.get<Blob>('/references/clients/template', { responseType: 'blob' }),

  exportExcel: () =>
    api.get<Blob>('/references/clients/export', { responseType: 'blob' }),

  preview: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post<ApiSuccess<ClientUploadPreview>>('/references/clients/preview', form)
  },

  upload: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post<ApiSuccess<ClientUploadResult>>('/references/clients/upload', form)
  },
}
