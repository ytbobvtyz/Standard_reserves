import api from './client'
import type {
  ApiSuccess,
  StockDynamicsBounds,
  StockDynamicsData,
  StockDynamicsParams,
  StockSummaryData,
} from './types'

export const analyticsApi = {
  getStockDynamics: (params: StockDynamicsParams) =>
    api.get<ApiSuccess<StockDynamicsData>>('/analytics/stock-dynamics', { params }),

  getStockBounds: (
    params: Omit<StockDynamicsParams, 'date_from' | 'date_to' | 'granularity'>,
  ) =>
    api.get<ApiSuccess<StockDynamicsBounds>>('/analytics/stock-dynamics/bounds', {
      params,
    }),

  getStockSummary: (
    params: Omit<StockDynamicsParams, 'date_from' | 'date_to' | 'granularity'>,
  ) => api.get<ApiSuccess<StockSummaryData>>('/analytics/stock-summary', { params }),
}
