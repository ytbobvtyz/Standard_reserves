import api from './client'
import type {
  ActualShipmentListItem,
  ActualShipmentListParams,
  ActualShipmentUploadResult,
  ApiSuccess,
} from './types'

export const actualShipmentsApi = {
  list: (params?: ActualShipmentListParams) =>
    api.get<ApiSuccess<ActualShipmentListItem[]>>('/logistics/actual-shipments', {
      params,
    }),

  downloadTemplate: () =>
    api.get<Blob>('/logistics/actual-shipments/template', { responseType: 'blob' }),

  upload: (file: File, confirm: boolean) => {
    const form = new FormData()
    form.append('file', file)
    return api.post<ApiSuccess<ActualShipmentUploadResult>>(
      '/logistics/actual-shipments/upload',
      form,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        params: { confirm: confirm ? 'true' : 'false' },
      },
    )
  },
}
