import api from './client'
import type {
  ApiSuccess,
  DashboardExceptionItem,
  DashboardExceptionParams,
  DashboardMassUnit,
  DashboardSummary,
  DashboardTrendData,
  DashboardTrendParams,
  ExpiryCalendarData,
  NzByDepartmentData,
  TopClientsData,
  WarehouseCoverageData,
} from './types'

export const dashboardApi = {
  getSummary: (params?: { unit?: DashboardMassUnit; warehouse_code?: number }) =>
    api.get<ApiSuccess<DashboardSummary>>('/dashboard/summary', { params }),

  getNormativeTrend: (params?: DashboardTrendParams) =>
    api.get<ApiSuccess<DashboardTrendData>>('/dashboard/normative-trend', { params }),

  getExceptions: (params?: DashboardExceptionParams) =>
    api.get<ApiSuccess<DashboardExceptionItem[]>>('/dashboard/exceptions', { params }),

  getWarehouseCoverage: (params?: {
    unit?: DashboardMassUnit
    warehouse_code?: number
  }) =>
    api.get<ApiSuccess<WarehouseCoverageData>>('/dashboard/warehouse-coverage', {
      params,
    }),

  getExpiryCalendar: (params?: {
    date_from?: string
    date_to?: string
    unit?: DashboardMassUnit
    warehouse_code?: number
  }) => api.get<ApiSuccess<ExpiryCalendarData>>('/dashboard/expiry-calendar', { params }),

  getNzByDepartment: (params?: { unit?: DashboardMassUnit }) =>
    api.get<ApiSuccess<NzByDepartmentData>>('/dashboard/nz-by-department', { params }),

  getTopClients: (params?: { unit?: DashboardMassUnit; limit?: number }) =>
    api.get<ApiSuccess<TopClientsData>>('/dashboard/top-clients', { params }),
}
