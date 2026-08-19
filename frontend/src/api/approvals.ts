import api from './client'
import type {
  ApiSuccess,
  ApprovalActionPayload,
  ApprovalActionResult,
  ApprovalListParams,
  ApprovalPendingRequest,
} from './types'

export const approvalsApi = {
  getPPPending: (params?: ApprovalListParams) =>
    api.get<ApiSuccess<ApprovalPendingRequest[]>>('/approvals/pp/pending', { params }),

  ppAction: (id: string, data: ApprovalActionPayload) =>
    api.post<ApiSuccess<ApprovalActionResult>>(`/approvals/pp/${id}/action`, data),

  getEconomyPending: (params?: ApprovalListParams) =>
    api.get<ApiSuccess<ApprovalPendingRequest[]>>('/approvals/economy/pending', {
      params,
    }),

  economyAction: (id: string, data: ApprovalActionPayload) =>
    api.post<ApiSuccess<ApprovalActionResult>>(`/approvals/economy/${id}/action`, data),
}
