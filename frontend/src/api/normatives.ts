import api from './client'
import type {
  ApiSuccess,
  NormativeListItem,
  NormativeListParams,
  NormativeOnDateItem,
  NormativeOnDateParams,
} from './types'

export const normativesApi = {
  list: (params?: NormativeListParams) =>
    api.get<ApiSuccess<NormativeListItem[]>>('/normatives', { params }),

  getOnDate: (params: NormativeOnDateParams) =>
    api.get<ApiSuccess<NormativeOnDateItem[]>>('/normatives/on-date', { params }),
}
