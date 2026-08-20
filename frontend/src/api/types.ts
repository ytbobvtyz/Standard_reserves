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

export type ApprovalAction = 'approve' | 'edit' | 'reject'

export interface ApprovalPendingItem {
  product_code: number
  product_name: string
  warehouse_code: number
  warehouse_name: string
  quantity_requested: number
  quantity_approved: number | null
  unit: Unit
}

export interface ApprovalPendingRequest {
  id: string
  request_type: RequestType
  client_name: string
  initiator: User
  items: ApprovalPendingItem[]
  created_at: string
}

export interface ApprovalActionPayload {
  action: ApprovalAction
  items?: Array<{
    product_code: number
    warehouse_code: number
    quantity_approved: number
  }>
  comment?: string
}

export interface ApprovalActionResult {
  id: string
  status: RequestStatus
  pp_approved_at?: string | null
  pp_approved_by?: { id: string; full_name: string } | null
  pp_action?: ApprovalAction | null
  comment_pp?: string | null
  economy_approved_at?: string | null
  economy_approved_by?: { id: string; full_name: string } | null
  economy_action?: ApprovalAction | null
  comment_economy?: string | null
}

export interface ApprovalListParams {
  type?: RequestType
  page?: number
  limit?: number
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

export type FilterMode = 'all' | 'with_normatives' | 'deficit_only'
export type DeficitStatus = 'warning' | 'ok'

export interface LogisticsDashboardParams {
  warehouse_code?: number
  filter_mode?: FilterMode
  unit?: Unit
}

export interface DeficitItem {
  product_code: number
  product_name: string
  category: string
  normative_quantity: number
  fact_quantity: number
  unit: Unit
  deficit: number
  client_name: string
  expiry_date: string | null
  status: DeficitStatus
}

export interface WarehouseDeficit {
  warehouse_code: number
  warehouse_name: string
  deficit_items: DeficitItem[]
  total_deficit: number
  deficit_count: number
}

export interface LogisticsDashboardSummary {
  total_deficit: number
  deficit_warehouses: number
  deficit_products: number
}

export interface LogisticsDashboardData {
  status: 'success'
  data: WarehouseDeficit[]
  summary: LogisticsDashboardSummary
}

export interface GeneratedOrderItem {
  product_code: number
  product_name: string
  deficit: number
  unit: Unit
}

export interface GeneratedOrder {
  plant_code: number
  plant_name: string
  warehouse_code: number
  warehouse_name: string
  items: GeneratedOrderItem[]
  estimated_delivery_days: number
}

export interface GenerateOrdersData {
  orders: GeneratedOrder[]
  total_orders: number
  total_products: number
  total_quantity: number
}

export interface GenerateOrdersPayload {
  product_codes?: number[]
}

export interface GenerateOrdersBulkPayload {
  warehouse_codes: number[]
  product_codes?: number[]
}

export interface OneTimeListParams {
  warehouse_code?: number
  client_name?: string
  initiator_id?: string
  from_date?: string
  to_date?: string
  status?: RequestStatus
  page?: number
  limit?: number
}

export interface OneTimeItem {
  product_code: number
  product_name: string
  warehouse_code: number
  warehouse_name: string
  quantity: number
  unit: Unit
}

export interface OneTimeListItem {
  id: string
  client_name: string
  status: RequestStatus
  initiator: User
  items: OneTimeItem[]
  created_at: string
  order_number?: string | null
  executed_at?: string | null
}

export interface OneTimeInitiator {
  id: string
  username: string
  full_name: string
}

export interface ExecuteOneTimePayload {
  order_number: string
  comment?: string
}

export interface ExecuteOneTimeData {
  id: string
  status: RequestStatus
  executed_at: string
  executed_by: string
  order_number: string
  executed_comment?: string | null
}
