import api from './client'
import type {
  ApiSuccess,
  ObjectListItem,
  ObjectListParams,
  ProductListItem,
  ProductListParams,
  User,
} from './types'

export const referencesApi = {
  getProducts: (params?: ProductListParams) =>
    api.get<ApiSuccess<ProductListItem[]>>('/references/products', { params }),

  getProduct: (code: number) =>
    api.get<ApiSuccess<ProductListItem>>(`/references/products/${code}`),

  getObjects: (params?: ObjectListParams) =>
    api.get<ApiSuccess<ObjectListItem[]>>('/references/objects', { params }),

  getObject: (code: number) =>
    api.get<ApiSuccess<ObjectListItem>>(`/references/objects/${code}`),

  getUsers: () => api.get<ApiSuccess<User[]>>('/references/users'),
}
