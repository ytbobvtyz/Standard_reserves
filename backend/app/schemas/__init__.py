"""Pydantic schemas."""

from app.schemas.approval import (
    ApprovalActionRequest,
    ApprovalActionResult,
    ApprovalPendingRequest,
)
from app.schemas.auth import (
    AccessTokenData,
    LoginRequest,
    RefreshRequest,
    TokenPairData,
)
from app.schemas.common import MessageResponse, PaginatedResponse, SuccessResponse
from app.schemas.logistics import (
    DashboardResponse,
    GenerateOrdersBulkRequest,
    GenerateOrdersData,
    GenerateOrdersRequest,
)
from app.schemas.normative import (
    NormativeCalculateData,
    NormativeListItem,
    NormativeOnDateItem,
)
from app.schemas.reference import (
    ObjectListItem,
    ProductDetail,
    ProductListItem,
    RelatedProductsData,
    UserReference,
)
from app.schemas.request import (
    RequestCreate,
    RequestCreated,
    RequestDetail,
    RequestItemHistoryEntry,
    RequestListItem,
    RequestStatusData,
    RequestUpdate,
)
from app.schemas.user import ChangePasswordRequest, UserBrief, UserProfile

__all__ = [
    "AccessTokenData",
    "ApprovalActionRequest",
    "ApprovalActionResult",
    "ApprovalPendingRequest",
    "ChangePasswordRequest",
    "DashboardResponse",
    "GenerateOrdersBulkRequest",
    "GenerateOrdersData",
    "GenerateOrdersRequest",
    "LoginRequest",
    "MessageResponse",
    "NormativeCalculateData",
    "NormativeListItem",
    "NormativeOnDateItem",
    "ObjectListItem",
    "PaginatedResponse",
    "ProductDetail",
    "ProductListItem",
    "RefreshRequest",
    "RelatedProductsData",
    "RequestCreate",
    "RequestCreated",
    "RequestDetail",
    "RequestItemHistoryEntry",
    "RequestListItem",
    "RequestStatusData",
    "RequestUpdate",
    "SuccessResponse",
    "TokenPairData",
    "UserBrief",
    "UserProfile",
    "UserReference",
]
