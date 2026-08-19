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
from app.schemas.reference import (
    ObjectListItem,
    ProductDetail,
    ProductListItem,
    UserReference,
)
from app.schemas.request import (
    RequestCreate,
    RequestCreated,
    RequestDetail,
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
    "LoginRequest",
    "MessageResponse",
    "ObjectListItem",
    "PaginatedResponse",
    "ProductDetail",
    "ProductListItem",
    "RefreshRequest",
    "RequestCreate",
    "RequestCreated",
    "RequestDetail",
    "RequestListItem",
    "RequestStatusData",
    "RequestUpdate",
    "SuccessResponse",
    "TokenPairData",
    "UserBrief",
    "UserProfile",
    "UserReference",
]
