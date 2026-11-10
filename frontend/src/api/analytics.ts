import type { AxiosRequestConfig } from 'axios'
import api from './client'
import type {
  AnalyticsFiltersData,
  ApiSuccess,
  StockDynamicsBounds,
  StockDynamicsData,
  StockDynamicsParams,
  StockSummaryData,
} from './types'

function analyticsConfig(params: object): AxiosRequestConfig {
  return {
    params,
    paramsSerializer: {
      serialize: (input) => {
        const search = new URLSearchParams()
        for (const [key, value] of Object.entries(input as Record<string, unknown>)) {
          if (value === undefined || value === null) {
            continue
          }
          if (Array.isArray(value)) {
            if (value.length === 0) {
              search.append(key, '')
            } else {
              for (const item of value) {
                search.append(key, String(item))
              }
            }
            continue
          }
          search.append(key, String(value))
        }
        return search.toString()
      },
    },
  }
}

export const analyticsApi = {
  getFilters: (params: { product_code?: number } = {}) =>
    api.get<ApiSuccess<AnalyticsFiltersData>>('/analytics/filters', analyticsConfig(params)),

  getStockDynamics: (params: StockDynamicsParams) =>
    api.get<ApiSuccess<StockDynamicsData>>(
      '/analytics/stock-dynamics',
      analyticsConfig(params),
    ),

  getStockBounds: (
    params: Omit<StockDynamicsParams, 'date_from' | 'date_to' | 'granularity'>,
  ) =>
    api.get<ApiSuccess<StockDynamicsBounds>>(
      '/analytics/stock-dynamics/bounds',
      analyticsConfig(params),
    ),

  getStockSummary: (
    params: Omit<StockDynamicsParams, 'date_from' | 'date_to' | 'granularity'>,
  ) =>
    api.get<ApiSuccess<StockSummaryData>>(
      '/analytics/stock-summary',
      analyticsConfig(params),
    ),
}
