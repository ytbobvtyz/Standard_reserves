export type UserRole = 'commercial' | 'pp' | 'economist' | 'logistics' | 'guest'

export type RequestType = 'normative' | 'one_time'
export type RequestStatus =
  | 'draft'
  | 'pp_approved'
  | 'economy_check'
  | 'pp_rework'
  | 'economy_rework'
  | 'active'
  | 'approved'
  | 'rejected'
  | 'expired'
  | 'executed'
export type Unit = 'шт' | 'т'
export type ObjectType = 'plant' | 'warehouse'

export interface User {
  id: string
  username: string
  full_name: string
  role: UserRole
  department?: string | null
  email?: string
  last_login_at?: string | null
  is_active?: boolean
}

export interface PaginationMeta {
  page: number
  limit: number
  total: number
}

export interface ApiSuccess<T> {
  status: 'success'
  data: T
  meta?: PaginationMeta
}

export interface ApiErrorBody {
  status: 'error'
  error: {
    code: string
    message: string
    details?: Array<{ field?: string; message: string }>
  }
}

export interface LoginData {
  access_token: string
  refresh_token: string
  expires_in: number
  user: User
}

export interface RefreshData {
  access_token: string
  expires_in: number
}

export interface ProductListItem {
  code: number
  name: string
  category: string
  plant_id: number
  plant_name: string
  weight_kg: number
  monthly_consumption: number | null
  is_active: boolean
  description?: string | null
}

export interface ObjectListItem {
  code: number
  name: string
  city: string
  region?: string | null
  address?: string | null
  type: ObjectType
  is_active: boolean
}

export interface RequestItemPayload {
  product_code: number
  warehouse_code: number
  quantity_requested: number
  unit: Unit
  comment?: string
}

export interface RequestCreatePayload {
  request_type: RequestType
  client_name: string
  expiry_date?: string | null
  items: RequestItemPayload[]
  comment?: string
}

export interface RequestListItem {
  id: string
  request_type: RequestType
  status: RequestStatus
  client_name: string
  initiator: User
  items_count: number
  total_quantity: number
  expiry_date: string | null
  created_at: string
}

export interface RequestItemDetail {
  id: string
  product: {
    code: number
    name: string
    category: string
    weight_kg: number
  }
  warehouse: {
    code: number
    name: string
  }
  quantity_requested: number
  quantity_approved: number | null
  unit: Unit
  comment: string | null
}

export interface RequestHistoryEntry {
  timestamp: string
  action: string
  user_name: string | null
  comment: string | null
}

export interface RequestDetail {
  id: string
  request_type: RequestType
  status: RequestStatus
  client_name: string
  initiator: User
  initiator_comment: string | null
  comment_pp: string | null
  comment_economy: string | null
  expiry_date: string | null
  items: RequestItemDetail[]
  history: RequestHistoryEntry[]
  created_at: string
  updated_at: string
}

export interface RequestStatusData {
  id: string
  status: RequestStatus
  updated_at: string
}

export interface RequestListParams {
  type?: RequestType
  status?: RequestStatus
  client_name?: string
  page?: number
  limit?: number
}

export interface ProductListParams {
  search?: string
  category?: 'A' | 'B' | 'C'
  is_active?: boolean
  page?: number
  limit?: number
}

export interface ObjectListParams {
  type?: ObjectType
  city?: string
  is_active?: boolean
  page?: number
  limit?: number
}
