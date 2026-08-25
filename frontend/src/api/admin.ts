import api from './client'
import type {
  AdminUser,
  AdminUserCreatePayload,
  AdminUserListParams,
  AdminUserUpdatePayload,
  ApiSuccess,
  DepartmentListItem,
  PasswordResetData,
} from './types'

export const adminApi = {
  getUsers: (params?: AdminUserListParams) =>
    api.get<ApiSuccess<AdminUser[]>>('/admin/users', { params }),

  createUser: (data: AdminUserCreatePayload) =>
    api.post<ApiSuccess<AdminUser>>('/admin/users', data),

  getUser: (id: string) => api.get<ApiSuccess<AdminUser>>(`/admin/users/${id}`),

  updateUser: (id: string, data: AdminUserUpdatePayload) =>
    api.put<ApiSuccess<AdminUser>>(`/admin/users/${id}`, data),

  deleteUser: (id: string) =>
    api.delete<{ status: 'success'; message: string }>(`/admin/users/${id}`),

  resetPassword: (id: string) =>
    api.post<ApiSuccess<PasswordResetData>>(`/admin/users/${id}/reset-password`),

  getDepartments: () => api.get<ApiSuccess<DepartmentListItem[]>>('/admin/departments'),

  createDepartment: (data: { name: string }) =>
    api.post<ApiSuccess<DepartmentListItem>>('/admin/departments', data),

  updateDepartment: (id: string, data: { name: string }) =>
    api.put<ApiSuccess<DepartmentListItem>>(`/admin/departments/${id}`, data),

  deleteDepartment: (id: string) =>
    api.delete<{ status: 'success'; message: string }>(`/admin/departments/${id}`),
}
