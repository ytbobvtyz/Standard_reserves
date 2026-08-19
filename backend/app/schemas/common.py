from pydantic import BaseModel, Field


class SuccessResponse[T](BaseModel):
    status: str = Field(default="success")
    data: T


class MessageResponse(BaseModel):
    status: str = Field(default="success")
    message: str
