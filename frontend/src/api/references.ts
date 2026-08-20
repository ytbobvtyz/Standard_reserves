import api from './client'
import type {
  ApiSuccess,
  ObjectListItem,
  ObjectListParams,
  ProductDetail,
  ProductListItem,
  ProductListParams,
  ProductUpdatePayload,
  ProductUploadResult,
  RelatedProductsData,
  User,
} from './types'

export const referencesApi = {
  getProducts: (params?: ProductListParams) =>
    api.get<ApiSuccess<ProductListItem[]>>('/references/products', { params }),

  getProduct: (code: number) =>
    api.get<ApiSuccess<ProductDetail>>(`/references/products/${code}`),

  getProductForEdit: (code: number) =>
    api.get<ApiSuccess<ProductDetail>>(`/references/products/${code}/edit`),

  updateProduct: (code: number, payload: ProductUpdatePayload) =>
    api.put<ApiSuccess<ProductDetail>>(`/references/products/${code}`, payload),

  deleteProduct: (code: number) =>
    api.delete<{ status: 'success'; message: string }>(`/references/products/${code}`),

  downloadProductsTemplate: () =>
    api.get<Blob>('/references/products/template', { responseType: 'blob' }),

  uploadProducts: (file: File, onProgress?: (percent: number) => void) => {
    const form = new FormData()
    form.append('file', file)
    return api.post<ApiSuccess<ProductUploadResult>>(
      '/references/products/upload',
      form,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (event) => {
          if (event.total) {
            onProgress?.(Math.round((event.loaded / event.total) * 100))
          }
        },
      },
    )
  },

  getRelated: (code: number) =>
    api.get<ApiSuccess<RelatedProductsData>>(`/products/${code}/related`),

  getObjects: (params?: ObjectListParams) =>
    api.get<ApiSuccess<ObjectListItem[]>>('/references/objects', { params }),

  getObject: (code: number) =>
    api.get<ApiSuccess<ObjectListItem>>(`/references/objects/${code}`),

  getUsers: () => api.get<ApiSuccess<User[]>>('/references/users'),
}
